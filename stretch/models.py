import os
import math
import logging
import tarfile
import json
import time
import jsonfield
import uuidfield
from contextlib import contextmanager
from distutils import dir_util
from django.db import models
from django.db.models import signals as model_signals
from django.dispatch import receiver
from django.core.validators import RegexValidator
from django.conf import settings
from celery import current_task, group
from celery.contrib.methods import task

from stretch import (signals, sources, utils, backends, parser, exceptions,
                     config_managers)
from stretch.salt_api import salt_client, wheel_client, runner_client


log = logging.getLogger('stretch')
config_manager = config_managers.get_config_manager()
alphanumeric = RegexValidator(r'^[a-zA-Z0-9_\-]*$',
                              'Only alphanumeric characters, underscores, and '
                              'hyphens are allowed.')


class AuditedModel(models.Model):
    """
    Provides `created_at` and `updated_at` fields to indicate when the model
    was modified.
    """
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class System(AuditedModel):
    """
    Stateful container for environments.
    """
    name = models.TextField(unique=True, validators=[alphanumeric])
    domain_name = models.TextField(unique=True, null=True)

    def create_release(self, options):
        return Release.create(self.source.pull(options), system=self)

    def sync_source(self, nodes=None):
        if hasattr(self.source, 'autoload') and self.source.autoload:
            for env in self.environments.all():
                if env.backend.autoloads and nodes:
                    env.autoload.delay(self.source, nodes)
                elif env.backend.autoloads:
                    env.deploy.delay(self.source)
                else:
                    log.debug('Backend does not autoload. Skipping.')

    @property
    @utils.memoized
    def source(self):
        """
        Returns the correct source to be used with the system. (Only one
        source is used per system for now. Multiple source handling may be
        implemented.)
        """
        system_sources = sources.get_sources(self)
        if not system_sources:
            raise exceptions.UndefinedSource()
        return system_sources[0]

    @property
    @utils.memoized
    def config_manager(self):
        return config_managers.get_config_manager()


class Environment(AuditedModel):
    """
    Stateful container for hosts, instances, and groups.
    """

    name = models.TextField(validators=[alphanumeric])
    auto_deploy = models.BooleanField(default=False)
    system = models.ForeignKey('System', related_name='environments')
    current_release = models.ForeignKey('Release', null=True)
    using_source = models.BooleanField(default=False)
    config = jsonfield.JSONField(default={})
    app_paths = jsonfield.JSONField(default={})

    @property
    @utils.memoized
    def backend(self):
        """
        Returns the correct backend to be used with the current environment.
        """
        return backends.get_backend(self)

    @task
    def deploy(self, obj):
        """
        Deploys any release or source to the environment.

        TODO: Multiple deploy tasks should not be able to run concurrently on
        a single environment.

        :Parameters:
          - `obj`: a release or source.
        """
        log.info('Deploying %s to %s/%s' % (obj, self.system.name, self.name))

        if hasattr(obj, 'pull'):
            # Object is source
            deploy = self._save_deploy(current_task)
            self.current_release = None
            self.using_source = True
        elif hasattr(obj, 'sha'):
            # Object is release
            deploy = self._save_deploy(current_task, obj)
            if self.current_release:
                deploy.existing_snapshot = self.current_release.get_snapshot()
            self.current_release = obj
            self.using_source = False
        else:
            raise Exception('unable to deploy object "%s"' % obj)

        self._deploy_obj(obj, deploy)

    @task
    def autoload(self, source, nodes):
        """
        Called indirectly by the `sync_source` signal. Only functions if the
        environment's backend can autoload.

        :Parameters:
          - `source`: the source to run build plugins on.
          - `nodes`: a list of parser nodes that were changed in the autoload.
        """
        if self.backend.autoloads:
            log.info('Autoloading %s' % source)

            # Use stub deploy for plugins. This deploy is not saved because it
            # represents a minor, incremental change.
            deploy = Deploy.create(environment=self)

            # Only build plugins are run because, unlike files related to build
            # plugins like images and assets, changing files related to deploy
            # plugins will never trigger an autoload.
            source.run_build_plugins(deploy, nodes)
            node_names = [node.name for node in nodes]
            for instance in self.instances.all():
                if instance.node.name in node_names:
                    # A simple `reload()` is sufficient to load any file
                    # changes and restart processes. A `restart()` would have
                    # been called if the Docker node image were recompiled.
                    instance.reload()

    def _save_deploy(self, deploy_task, release=None):
        """
        Called when the deploy has officially started. A record of the deploy
        is saved and returned for further usage in the pipeline.

        :Parameters:
          - `deploy_task`: the celery task performing the deploy.
          - `release`: the release being deployed.
        """
        deploy = Deploy.create(
            environment=self,
            existing_release=self.current_release,
            release=release,
            task_id=deploy_task.request.id
        )
        deploy.save()
        return deploy

    def _deploy_obj(self, obj, deploy):
        """
        Deploy a release or source to all instances and hosts in the
        environment.

        :Parameters:
          - `obj`: an object assumed to be a release or source.
          - `deploy`: the corresponding `Deploy` object
        """
        snapshot = obj.get_snapshot()
        with deploy.start(snapshot):
            if self.using_source:
                # WARNING: If celery is used for deploying instances, app_paths
                # will have to be saved in order to persist across processes.
                # Since instances and hosts are deployed to by threads instead
                # of separate processes, this is not a concern.
                self.app_paths = snapshot.get_app_paths()
                # Build new images for source
                snapshot.build_and_push(None, self.system)
                self._deploy_to_instances()
            else:
                # Object is release
                # The release can be deployed immediately since the source
                # images were compiled and pushed when the release was created.
                self._deploy_to_instances(obj.sha)
        self.save()

    def _deploy_to_instances(self, sha=None):
        # TODO: make tasks non-concurrent, (celery locks)
        batch_size = min(int(math.ceil(self.instances.count() / 2.0)),
                         settings.STRETCH_BATCH_SIZE)

        host.pull_nodes(sha)

    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        """
        Adds the environment to the config manager if new. Environment
        configuration will be saved on every save. This allows the config
        manager to propagate changes to an environment's `config`.
        """
        env = instance
        if created:
            env.system.config_manager.add_env(env)
        env.system.config_manager.sync_env_config(env)

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
        """
        Removes the environment from the config manager.
        """
        env = instance
        env.system.config_manager.remove_env(env)


model_signals.post_save.connect(Environment.post_save, sender=Environment)
model_signals.pre_delete.connect(Environment.pre_delete, sender=Environment)


class Release(AuditedModel):
    name = models.TextField()
    sha = models.CharField('SHA', max_length=28)
    system = models.ForeignKey('System', related_name='releases')
    unique_together = ('system', 'name', 'sha')

    @classmethod
    def create(cls, path, system):
        release = cls(
            name=utils.generate_memorable_name(),
            sha=utils.generate_random_hex(28),
            system=system
        )

        # Copy to temporary directory
        tmp_path = utils.temp_dir(path)

        # Create snapshot
        snapshot = parser.Snapshot(tmp_path)

        # Build release from snapshot
        # Archive the release
        release_dir = release.get_data_dir()
        utils.clear_path(release_dir)

        # Tar release buffer
        tar_path = os.path.join(release_dir, 'snapshot.tar.gz')
        tar_file = tarfile.open(tar_path, 'w:gz')
        tar_file.add(tmp_path, '/')
        tar_file.close()

        # Build docker images
        snapshot.build_and_push(release, system)

        # Delete snapshot buffer
        utils.delete_path(tmp_path)

        # Build finished
        release.save()
        signals.release_created.send(sender=release)
        return release

    def get_snapshot(self):
        tar_path = os.path.join(self.get_data_dir(), 'snapshot.tar.gz')
        tmp_path = utils.temp_dir()
        tar_file = tarfile.open(tar_path)
        tar_file.extractall(tmp_path)
        tar_file.close()
        return parser.Snapshot(tmp_path)

    def get_data_dir(self):
        return os.path.join(settings.STRETCH_DATA_DIR, 'releases', self.sha)


class Port(AuditedModel):
    node = models.ForeignKey('Node', related_name='ports')
    name = models.TextField(validators=[alphanumeric])
    number = models.IntegerField()


class Node(AuditedModel):
    name = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='nodes')
    unique_together = ('system', 'name')

    def get_image(self, local=False, private=False):
        if local:
            prefix = stretch_agent
        elif private:
            prefix = settings.STRETCH_REGISTRY_PRIVATE_URL
        else:
            prefix = settings.STRETCH_REGISTRY_PUBLIC_URL
        return '%s/sys%s/%s' % (prefix, self.system.pk, self.name)


class Instance(AuditedModel):
    id = uuidfield.UUIDField(auto=True, primary_key=True)

    environment = models.ForeignKey('Environment', related_name='instances')
    host = models.ForeignKey('Host', related_name='instances')
    node = models.ForeignKey('Node', related_name='instances')

    @classmethod
    def create(cls, env, host, node):
        instance = cls(environment=env, host=host, node=node)
        instance.save()
        instance.host.agent.add_instance(instance)

    # CHANGE
    def get_endpoint(self):
        # Get the instance's current endpoint from the config manager
        pass

    def reload(self):
        self.host.agent.reload_instance(self)

    def restart(self):
        self.host.agent.restart_instance(self)

    @property
    def config_key(self):
        return self.environment.system.config_manger.get_instance_key(self)

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
        instance.host.agent.remove_instance(instance)


model_signals.pre_delete.connect(Instance.pre_delete, sender=Instance)


class LoadBalancer(models.Model):
    id = uuidfield.UUIDField(auto=True, primary_key=True)
    host_port = models.IntegerField()
    #Enum
    #protocol = models.TextField(choice=())
    address = models.GenericIPAddressField()
    backend_id = models.CharField(max_length=32, unique=True)

    def activate_with_hosts(self, hosts):
        self.address = self.get_backend().create_lb(self, hosts, str(self.pk))

    def get_backend(self):
        backend = self.group.environment.backend
        if not backend:
            raise Exception('no backend defined')
        return self.group.environment.backend

    def add_host(self, host):
        self.get_backend().lb_add_host(self, host)

    def remove_host(self, host):
        self.get_backend().lb_remove_host(self, host)

    def delete(self):
        self.get_backend().delete_lb(self)
        super(LoadBalancer, self).delete()


class Host(AuditedModel):
    fqdn = models.TextField(unique=True)
    name = models.TextField(unique=True)
    hostname = models.TextField()
    domain_name = models.TextField(null=True)
    group = models.ForeignKey('Group', related_name='hosts', null=True)
    environment = models.ForeignKey('Environment', related_name='hosts')
    address = models.GenericIPAddressField()

    @classmethod
    def create(cls, env, group=None):
        # No group means unmanaged host
        domain_name = env.system.domain_name
        hostname = (utils.generate_random_hex(8) if group
                    else fqdn.replace(domain_name, ''))
        fqdn = '%s.%s' % (hostname, domain_name) if domain_name else hostname

        host = cls(fqdn=fqdn, name=name, hostname=hostname,
                   domain_name=domain_name, environment=env, group=group)

        if group:
            # Managed host
            if not env.backend:
                raise exceptions.UndefinedBackend()
            host.address = env.backend.create_host(host)

        host.finish_provisioning()
        log.info('Saving host...')
        host.save()

        if group:
            # Managed host
            log.info('Creating new instance for host...')
            host.create_instance(group.node)

        return host

    def pull_nodes(self, sha=None):
        # TODO: make this concurrent
        nodes = []
        for instance in self.instances.all():
            if instance.node not in nodes:
                nodes.append(instance.node)
                self.agent.pull(instance.node, sha)

    def create_instance(self, node):
        Instance.create(self.environment, self, node)

    def finish_provisioning(self):
        self.accept_key()
        self.sync()

    def accept_key(self):
        log.info('Accepting minion key (%s)...' % self.fqdn)

        success = False
        for _ in xrange(30):
            result = wheel_client().call_func('key.accept', match=self.fqdn)
            if result != {}:
                success = True
                break
            time.sleep(2.0)

        if success:
            log.info('Accepted minion key')
        else:
            raise Exception('failed to accept minion key')

    def delete_key(self):
        wheel_client().call_func('key.delete', match=self.fqdn)

    def sync(self):
        # Install dependencies
        log.info('Installing dependencies...')
        for _ in xrange(10):
            result = self.call('state.highstate')
            if result != {}:
                log.debug(result)
                break
        # Synchronize modules
        log.info('Synchronizing modules...')
        for _ in xrange(10):
            result = self.call('saltutil.sync_modules')
            if result != {}:
                log.debug(result)
                break

    def add_instance(self, instance):
        release = self.environment.current_release
        if not release and not self.environment.using_source:
            raise Exception('environment has no current release')
            # TODO: be able to add instance that wait for a deploy instead of
            # having to use a deploy at creation time
        sha = None
        if release:
            sha = release.sha
        utils.wait(self.instance_call(instance, 'stretch.add_instance',
                                      instance.get_deploy_options(sha)))

    def call(self, *args, **kwargs):
        return salt_client().cmd(self.fqdn, *args, **kwargs)

    @property
    @utils.memoized
    def agent(self):
        return AgentClient(self.address)

    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        host = instance
        if created and not host.group:
            log.info('Adding managed host to config manager...')
            host.environment.system.config_manager.add_managed_host(host)

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
        host = instance
        host.delete_key()
        if host.group:
            if not host.environment.backend:
                raise exceptions.UndefinedBackend()
            host.environment.backend.delete_host(host)
        else:
            host.environment.system.config_manager.remove_managed_host(host)


model_signals.post_save.connect(Host.post_save, sender=Host)
model_signals.pre_delete.connect(Host.pre_delete, sender=Host)


class Group(AuditedModel):
    name = models.TextField(validators=[alphanumeric])
    environment = models.ForeignKey('Environment', related_name='groups')
    minimum_nodes = models.IntegerField(default=1)
    maximum_nodes = models.IntegerField(null=True)
    node = models.ForeignKey('Node')
    load_balancer = models.OneToOneField('LoadBalancer', null=True)
    unique_together = ('environment', 'name')

    def scale_up(self, amount):
        self.check_valid_amount(self.hosts.count() + amount)
        group(self._create_host.s() for _ in xrange(amount))().get()

    def scale_down(self, amount):
        self.check_valid_amount(self.hosts.count() - amount)
        hosts = self.hosts.all()[0:amount]
        group(self._delete_host.s(host.pk) for host in hosts)().get()

    def create_load_balancer(self, port, host_port, protocol):
        if self.hosts.count() > 0:
            raise Exception('no hosts in group')
        if not self.load_balancer:
            self.load_balancer = LoadBalancer(port=port, host_port=host_port,
                                              protocol=protocol)
            self.load_balancer.activate_with_hosts(self.hosts.all())
            self.load_balancer.save()
        else:
            raise Exception('group already has a load balancer')

    def scale_to(self, amount):
        relative_amount = amount - self.hosts.count()
        if relative_amount > 0:
            self.scale_up(relative_amount)
        elif relative_amount < 0:
            self.scale_down(-relative_amount)

    def check_valid_amount(self, amount):
        if self.maximum_nodes == None:
            valid = amount >= self.minimum_nodes
        else:
            valid = self.minimum_nodes <= amount <= self.maximum_nodes
        if not valid:
            raise Exception('invalid scaling amount')

    @task
    def _create_host(self):
        host = Host.create(self.environment, self)
        if self.load_balancer:
            self.load_balancer.add_host(host)

    @task
    def _delete_host(self, host_id):
        host = Host.objects.get(pk=host_id)
        if self.load_balancer:
            self.load_balancer.remove_host(host)
        host.delete()


class Deploy(AuditedModel):
    release = models.ForeignKey('Release', related_name='deploy_releases',
                                null=True)
    existing_release = models.ForeignKey('Release',
        related_name='deploy_existing_releases', null=True)
    environment = models.ForeignKey('Environment', related_name='deploys')
    task_id = models.CharField(max_length=128, null=True)

    @classmethod
    def create(cls, *args, **kwargs):
        deploy = cls(*args, **kwargs)
        deploy.snapshot = None
        deploy.existing_snapshot = None
        return deploy

    @contextmanager
    def start(self, snapshot):
        self.snapshot = snapshot
        self.snapshot.run_build_plugins(self)
        self.snapshot.run_pre_deploy_plugins(self)
        template_path = os.path.join(settings.STRETCH_CACHE_DIR, 'templates',
                                     str(self.environment.pk))

        with self.snapshot.mount_templates(template_path):
            yield

        utils.clear_path(template_path)
        self.snapshot.run_post_deploy_plugins(self)
        utils.delete_path(self.snapshot.path)
        if self.existing_snapshot:
            utils.delete_path(self.existing_snapshot.path)

    @contextmanager
    def mount_templates(self, snapshot, path):
        utils.clear_path(path)
        for node in snapshot.nodes:
            try:
                node_obj = self.environment.system.nodes.get(name=node.name)
            except Node.DoesNotExist:
                pass
            else:
                dest_path = os.path.join(path, str(node_obj.pk))
                utils.clear_path(dest_path)
                templates_path = os.path.join(node.container.path, 'templates')
                if os.path.exists(templates_path):
                    dir_util.copy_tree(templates_path, dest_path)


@receiver(signals.sync_source)
def on_sync_source(sender, nodes, **kwargs):
    source = sender
    log.info('Source %s changed' % source)
    log.info('Changed nodes: %s' % nodes)
    system_name = sources.get_system(source)
    if system_name:
        system = System.objects.get(name=system_name)
        system.sync_source(nodes)


@receiver(signals.load_sources)
def on_load_sources(sender, **kwargs):
    log.info('Deploying autoloadable sources...')
    for system in System.objects.all():
        system.sync_source()


@receiver(signals.release_created)
def on_release_created(sender, **kwargs):
    release = sender
    for env in release.system.environments.all():
        if env.auto_deploy:
            env.deploy.delay(release)
