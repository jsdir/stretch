import os
import math
import logging
import tarfile
import json
import time
import jsonfield
import uuidfield
from contextlib import contextmanager
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
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True


class System(AuditedModel):
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
        # Only one source is used per system for now
        system_sources = sources.get_sources(self)
        if not system_sources:
            raise exceptions.UndefinedSource()
        return system_sources[0]

    @property
    @utils.memoized
    def config_manager(self):
        return config_managers.get_config_manager()


class Environment(AuditedModel):
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
        return backends.get_backend(self)

    # TODO: make tasks non-concurrent, (celery buckets)
    @task
    def deploy(self, obj):
        log.info('Deploying %s to %s/%s' % (obj, self.system.name, self.name))

        if hasattr(obj, 'pull'):
            deploy = self.save_deploy(current_task)
            self.current_release = None
            self.using_source = True
        else:
            deploy = self.save_deploy(current_task, obj)
            if self.current_release:
                deploy.existing_snapshot = self.current_release.get_snapshot()
            self.current_release = obj
            self.using_source = False

        snapshot = obj.get_snapshot()
        with deploy.start(snapshot):
            if self.using_source:
                # TODO: if celery is used for deploying instances, app_paths
                # will have to be saved in order to persist across processes
                self.app_paths = snapshot.get_app_paths()
                # Build new images specifically for source
                snapshot.build_and_push(None, self.system)
                self.deploy_to_instances(snapshot, nodes=snapshot.nodes)
            else:
                self.deploy_to_instances(snapshot, sha=obj.sha)

        self.save()

    @task
    def autoload(self, source, nodes):
        log.info('Autoloading %s' % source)

        # Use stub deploy
        deploy = Deploy.create(environment=self)

        source.run_build_plugins(deploy, nodes)
        node_names = [node.name for node in nodes]
        for instance in self.instances.all():
            if instance.node.name in node_names:
                instance.reload()

    def save_deploy(self, deploy_task, release=None):
        deploy = Deploy.create(
            environment=self,
            existing_release=self.current_release,
            release=release,
            task_id=deploy_task.request.id
        )
        deploy.save()
        return deploy

    def deploy_to_instances(self, snapshot, sha=None, nodes=None):

        def check(instance, is_finished, deactivated):

            def is_finished_job():
                """
                Pending: False
                Done:    !False (result)
                """
                result = is_finished()
                if result != False and deactivated:
                    instance.host.activate()
                return result

            return is_finished_job

        def deploy(instance):
            if sha:
                deactivated = instance.host.deactivate()
                return check(instance, instance.deploy(sha=sha), deactivated)
            elif nodes:
                for node in nodes:
                    if node.name == instance.node.name and node.app_path:
                        deactivated = instance.host.deactivate()
                        return check(instance, instance.deploy(), deactivated)

            return None

        template_path = os.path.join(settings.STRETCH_CACHE_DIR, 'templates',
                                     str(self.pk))
        with snapshot.mount_templates(template_path):
            self.map_instances(deploy)

    def map_instances(self, callback):
        batch_size = min(int(math.ceil(self.instances.count() / 2.0)),
                         settings.STRETCH_BATCH_SIZE)

        instances = []
        for instance in self.instances.all():
            instance.group = instance.host.group
            instances.append(instance)

        groups = utils.group_by_attr(instances, 'group')
        log.info('Mapping deploy to groups: %s @ %s' % (groups, batch_size))
        results = utils.map_groups(callback, groups, batch_size)

    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        env = instance
        if created:
            env.system.config_manager.add_env(env)
        env.system.config_manager.sync_env_config(env)

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
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

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
        log.info('Port pre_delete')

model_signals.pre_delete.connect(Port.pre_delete, sender=Port)

class Node(AuditedModel):
    name = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='nodes')
    unique_together = ('system', 'name')

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
        log.info('Node pre_delete')

model_signals.pre_delete.connect(Node.pre_delete, sender=Node)


class Instance(AuditedModel):
    id = uuidfield.UUIDField(auto=True, primary_key=True)

    environment = models.ForeignKey('Environment', related_name='instances')
    host = models.ForeignKey('Host', related_name='instances')
    node = models.ForeignKey('Node', related_name='instances')

    @classmethod
    def create(cls, env, host, node):
        instance = cls(environment=env, host=host, node=node)
        instance.save()
        instance.host.add_instance(instance)

    def get_deploy_options(self, sha=None):
        if sha:
            app_path = None
        else:
            app_path = self.environment.app_paths[self.node.name]

        system = self.environment.system
        ports = dict([(p.name, p.number) for p in self.node.ports.all()])

        return {
            'system_id': str(self.environment.system.pk),
            'env_id': str(self.environment.pk),
            'env_name': self.environment.name,
            'node_id': str(self.node.pk),
            'node_name': self.node.name,
            'node_ports': ports,
            'node_app_path': app_path,
            'registry_url': settings.STRETCH_REGISTRY_PRIVATE_URL,
            'instance_key': system.config_manager.get_instance_key(self),
            'sha': sha
        }

    def reload(self):
        return self.host.reload_instance(self)

    def restart(self):
        return self.host.restart_instance(self)

    def deploy(self, sha=None):
        return self.host.deploy_instance(self, sha)

    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        instance.environment.system.config_manager.add_instance(instance)

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
        instance.environment.system.config_manager.remove_instance(instance)
        instance.host.remove_instance(instance)


model_signals.post_save.connect(Instance.post_save, sender=Instance)
model_signals.pre_delete.connect(Instance.pre_delete, sender=Instance)


class LoadBalancer(models.Model):
    host_port = models.IntegerField()
    #Enum
    #protocol = models.TextField(choice=())
    address = models.GenericIPAddressField()
    backend_id = models.CharField(max_length=32, unique=True)

    def activate_with_hosts(self, hosts):
        backend = self.get_backend()
        self.backend_id, self.address = backend.create_lb(self, hosts)

    def get_backend(self):
        backend = self.group.environment.backend
        if not backend:
            raise Exception('no backend defined')
        return self.group.environment.backend

    def add_host(self, host):
        self.get_backend().lb_add_host(self, host)

    def remove_host(self, host):
        self.get_backend().lb_remove_host(self, host)

    def activate_host(self, host):
        self.get_backend().lb_activate_host(self, host)

    def deactivate_host(self, host):
        self.get_backend().lb_deactivate_host(self, host)

    def delete(self):
        self.get_backend().delete_lb(self)
        super(LoadBalancer, self).delete()


class Host(AuditedModel):
    fqdn = models.TextField(unique=True)
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

        host = cls(fqdn=fqdn, hostname=hostname, domain_name=domain_name,
                   environment=env, group=group)

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

    def activate(self):
        self.group.activate_host(self)

    def deactivate(self):
        deactivated = False
        if self.group and self.instances.count() > 1:
            self.group.deactivate_host(self)
            deactivated = True
        return deactivated

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

    def remove_instance(self, instance):
        utils.wait(self.instance_call(instance, 'stretch.remove_instance'))

    def reload_instance(self, instance):
        return self.instance_call(instance, 'stretch.reload')

    def restart_instance(self, instance):
        return self.instance_call(instance, 'stretch.restart')

    def deploy_instance(self, instance, sha=None):
        return self.instance_call(instance, 'stretch.deploy',
                                  instance.get_deploy_options(sha))

    def instance_call(self, instance, cmd, *args, **kwargs):
        args = [str(instance.pk)] + list(args)
        log.info('Calling instance -> %s (%s, %s)' % (self.fqdn, cmd, args))
        jid = salt_client().cmd_async(self.fqdn, cmd, args, **kwargs)

        def is_finished():
            #running_jids = runner_client().cmd('jobs.active', []).keys()
            #if jid in running_jids:
            #    log.info('Waiting for job [%s]...' % jid)
            #    return False
            #else:
            job = salt_client().get_cache_returns(jid)
            if job:
                result = job.values()[0]
                log.info('Job [%s] finished' % jid)
                log.debug(' - result: %s' % result)
                return result
            else:
                log.info('Waiting for job [%s]...' % jid)
                return False

        return is_finished

    def call(self, *args, **kwargs):
        return salt_client().cmd(self.fqdn, *args, **kwargs)

    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        host = instance
        if created and not host.group:
            log.info('Adding managed host to config manager...')
            host.environment.system.config_manager.add_managed_host(host)

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
        host = instance
        host.instances.all().delete()
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

    def activate_host(self, host):
        if self.load_balancer:
            self.load_balancer.activate_host(host)

    def deactivate_host(self, host):
        if self.load_balancer:
            self.load_balancer.deactivate_host(host)

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
        yield
        self.snapshot.run_post_deploy_plugins(self)
        utils.delete_path(self.snapshot.path)
        if self.existing_snapshot:
            utils.delete_path(self.existing_snapshot.path)


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
