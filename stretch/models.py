import os
import math
import logging
import tarfile
import json
import time
import uuid
import jsonfield
import uuidfield
from contextlib import contextmanager
from distutils import dir_util
from gevent import pool
from celery import current_task, group
from celery.contrib.methods import task

from django.db import models
from django.db.models import signals as model_signals
from django.dispatch import receiver
from django.core.validators import RegexValidator
from django.conf import settings

from stretch import (signals, sources, utils, backends, parser, exceptions,
                     config_managers)

from stretch.salt_api import salt_client, wheel_client
#from stretch.agent import supervisors
from stretch.agent.client import AgentClient


log = logging.getLogger('stretch')
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
        """
        Returns a memoized configuration manager (client) to be used with the
        system. Even though configuration mangers are structured to handle
        multiple systems, they are bound to systems in case different systems
        need different or separate configuration managers in the future.
        """
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
        environment. Also sets up context and builds images (if necessary) for
        the deploy.

        :Parameters:
          - `obj`: an object assumed to be a release or source.
          - `deploy`: the corresponding `Deploy` object
        """
        snapshot = obj.get_snapshot()
        with deploy.start(snapshot):
            if self.using_source:
                # Potential WARNING: If celery is used for deploying instances,
                # app_paths will have to be saved in order to persist across
                # processes. Since instances and hosts are deployed to by
                # threads instead of separate processes, this is not a concern
                # for now.
                self.app_paths = snapshot.get_app_paths()
                # Build new images for source
                snapshot.build_and_push(None, self.system)
                self._deploy_to_instances()
            else:
                # Object is release
                # The release can be deployed immediately since the source
                # images were compiled and pushed when the release was created.
                self._deploy_to_instances(obj)
        self.save()

    def _deploy_to_instances(self, release=None):
        """
        Pulls all associated nodes for every host in the environment. After the
        nodes are pulled, all associated instances are restarted. Since this
        task would consume too much time to perform sequentially, and since
        most of the subtasks involved are largely IO-bound, gevent is used
        to asynchronously pool and execute these sets of tasks.

        A host has to pull nodes before its instances can restart and use the
        updated node. In order to follow this constraint while retaining
        concurrency, host and instance pools are used. Execution is blocked
        until both of these pools become empty.

        Batch size is used as a form of rate limiting to prevent excessive
        load on the image registry. A batch size of five means that a maximum
        of five hosts can download images from the registry at the same time.
        When a host is finished, another host is added to the pool. This
        continues until all hosts have pulled their images. When a host is
        finished pulling its images and templates, all of its instances are
        added to an instance pool.

        An instance pool is given to every group in the environment. The
        concurrency of each pool is determined by the number of instances it
        contains.

        :Parameters:
          - `release`: the release to deploy. Left `None` if a source is being
          deployed.
        """

        group_pools = {None: pool.Group()}

        for group in self.groups.all():
            group_pools[group] = pool.Pool(group.batch_size)

        host_pool = pool.Pool(settings.STRETCH_BATCH_SIZE)
        for host in self.hosts.all():
            host_pool.spawn(host.pull_nodes, group_pools[host.group], release)

        host_pool.join()
        [p.join() for p in group_pools.values()]

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
    """
    A system state that can be deployed to environments, archived, and rolled
    back to.
    """
    name = models.TextField()
    sha = models.CharField('SHA', max_length=28)
    system = models.ForeignKey('System', related_name='releases')
    unique_together = ('system', 'name', 'sha')
    archive_name = 'snapshot.tar.gz'

    @classmethod
    def create(cls, path, system):
        """
        Creates, and processes, and archives a release. Emits a
        `release_created` signal upon completion.

        :Parameters:
          - `path`: the path to create the release from.
          - `system`: the system to associate the release with.
        """
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
        utils.clear_path(release.data_dir)

        # Tar release buffer
        tar_path = os.path.join(release.data_dir, cls.archive_name)
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
        """
        Extracts the release and returns a Snapshot.

        TODO: clean up the temporary path when finished.
        """
        tar_path = os.path.join(self.data_dir, self.archive_name)
        tmp_path = utils.temp_dir()
        tar_file = tarfile.open(tar_path)
        tar_file.extractall(tmp_path)
        tar_file.close()
        return parser.Snapshot(tmp_path)

    @property
    def data_dir(self):
        """
        Returns the archive directory for the release.
        """
        return os.path.join(settings.STRETCH_DATA_DIR, 'releases', self.sha)


class Port(AuditedModel):
    """
    A name:number port binding for Nodes.

    The stretch agent dynamically maps
    the ports of running containers. Having a name for a port allows one to
    choose between multiple port in a single endpoint in config.
    """
    node = models.ForeignKey('Node', related_name='ports')
    name = models.TextField(validators=[alphanumeric])
    number = models.IntegerField()


class Node(AuditedModel):
    """
    Node database abstraction that allows users to bind ports and their names.
    """
    name = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='nodes')
    unique_together = ('system', 'name')

    def get_image(self, local=False, private=False):
        """
        Returns the current image url for a node. Images may be stored locally,
        or may already be pushed to remote registries. The parameters will
        determine the image url.

        :Parameters:
          - `local`: `True` if the image is on the same machine as the stretch
          controller.
          - `private`: `True` if the image uses the registry's private url.
        """
        if local:
            prefix = 'stretch_agent'
        elif private:
            prefix = settings.STRETCH_REGISTRY_PRIVATE_URL
        else:
            prefix = settings.STRETCH_REGISTRY_PUBLIC_URL
        return '%s/sys%s/%s' % (prefix, self.system.pk, self.name)

    # TODO: Clean up deleted nodes here and when a host is deleted. An unmanaged
    # host may still have cached images.
    #
    # @classmethod
    # def pre_delete(cls, sender, instance, **kwargs):
    #     node = instance
    #     # Remove node from all host agents.
    #     instance.host.agent.remove_node(instance)
    #
    # model_signals.pre_delete.connect(Node.pre_delete, sender=Node)


class Instance(AuditedModel):
    """
    A running instance of a node.
    """
    id = uuidfield.UUIDField(auto=True, primary_key=True)
    environment = models.ForeignKey('Environment', related_name='instances')
    host = models.ForeignKey('Host', related_name='instances')
    node = models.ForeignKey('Node', related_name='instances')

    @classmethod
    def create(cls, env, host, node):
        """
        Creates an instance through the host's agent.

        :Parameters:
          - `env`: the instance's environment.
          - `host`: the instance's host.
          - `node`: the instance's node.
        """
        instance = cls(environment=env, host=host, node=node)
        instance.save()

        # Add the instance's node to the agent if it isn't there already.
        if node not in host.nodes:
            host.agent.add_node(node)
            if env.current_release:
                # Use the environment's release
                host.agent.pull(node, release=env.current_release)
            elif env.using_source:
                host.agent.pull(node)
            else:
                # Environment has not yet been deployed to
                pass

        host.agent.add_instance(instance)

    def reload(self):
        """
        Since reload is only used in development, there is no need to update
        the load balancer.
        """
        self.host.agent.reload_instance(self)

    @property
    def load_balancer(self):
        """
        Returns the instance's parent load balancer.
        """
        if self.host.group:
            return self.host.group.load_balancer
        return None

    @property
    def config_key(self):
        """
        Returns the instance's key in the configuration manager.
        """
        return self.environment.system.config_manger.get_instance_key(self)

    def restart(self):
        """
        When the agent restarts an instance, it restarts with the newest
        revision of the node. Restarting should take place after the host pulls
        its nodes.
        """
        # Restart instance
        self.safe_run(self.host.agent.restart_instance)

    def safe_run(self, func):
        """
        If the instance belongs to a load balancer, `func` is run while
        mirroring instance state to the load balancer.

        Restarting or removing any instance belonging to a load balancer
        uses a block/unblock pattern. This ensures that the endpoint manager
        does not remove the endpoint on its own. Since we must know the exact
        time the endpoint is removed from the load balancer, `_safe_run`
        removes it manually.

        :Parameters:
          - `func`: the function to safely run.
        """
        if self.load_balancer:
            # Have endpoint manager block (ignore) this instance
            endpoints = supervisors.endpoint_supervisor_client()
            endpoints.block_instance(self.pk)
            # Manually remove the instance's endpoint from the load balancer
            config_manager = self.environment.system.config_manger
            endpoint = config_manager.get(self.config_key)
            self.load_balancer.remove_endpoint(endpoint)

        # Run `func` now that instance state is mirrored to its load balancer
        func(self)

        if self.load_balancer:
            # Have endpoint manager unblock this instance
            endpoints.unblock_instance(self.pk)

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
        """
        Deletes the instance through the host's agent.
        """
        # Remove instance
        instance.safe_run(instance.host.agent.remove_instance)


model_signals.pre_delete.connect(Instance.pre_delete, sender=Instance)


class LoadBalancer(models.Model):
    """
    Load balancers adhere to a `protocol` -- http and tcp for now.

    For rackspace, the endpoint is set until the load balancer is deleted.
    For docker, the endpoint will change on each system startup.
    """
    id = uuidfield.UUIDField(primary_key=True)
    port_name = models.TextField(validators=[alphanumeric])
    protocol = models.CharField(max_length=10, choices=(
        ('http', 'http'),
        ('tcp', 'tcp')
    ))
    options = jsonfield.JSONField(default={})

    @classmethod
    def create(cls, group, port_name, protocol, options={}):
        """
        :Parameters:
          - `options`: {
                'securePort': 443,
                'sslTermination': True,
                'secureTrafficOnly': False,
                'certificate': '<cert>',
                'privatekey': '<key>'
            }
        """
        lb_id = uuid.uuid4().hex
        lb = cls(id=lb_id, port_name=port_name, protocol=protocol,
                 options=options)
        lb.group = group
        host, port = lb.backend.create_lb(lb)
        # Add key to config
        lb.group.environment.system.config_manager.set(lb.config_key,
            json.dumps({'host': host, 'port': port}))

        # Add group to endpoint supervisor
        endpoints = supervisors.endpoint_supervisor_client()
        endpoints.add_group(lb.group.pk, lb.group.config_key)
        lb.save()

    def add_endpoint(self, endpoint):
        """
        Chooses and adds an endpoint to the load balancer.

        :Parameters:
          - `endpoint`: {
            'host': '11.22.33.44',
            'ports': {'http': 80, 'https': 443}
          }
        """
        self._apply_endpoint(self.backend.lb_add_endpoint, endpoint)

    def remove_endpoint(self, endpoint):
        """
        Chooses and removes an endpoint from the load balancer.

        :Parameters:
          - `endpoint`: {
            'host': '11.22.33.44',
            'ports': {'http': 80, 'https': 443}
          }
        """
        self._apply_endpoint(self.backend.lb_remove_endpoint, endpoint)

    def _apply_endpoint(self, func, endpoint):
        host = endpoint['host']
        port = endpoint['ports'].get(self.port_name)
        if port != None:
            func(self, host, port)
        else:
            log.info('Unable to find port with name "%s"' % self.port_name)

    @property
    def backend(self):
        backend = self.group.environment.backend
        if not backend:
            raise Exception('no backend defined for environment')
        return backend

    @property
    def config_key(self):
        """
        Returns the load balancer's key in the configuration manager.
        """
        return self.environment.system.config_manger.get_lb_key(self)

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
        lb = instance
        # Remove group from endpoint supervisor
        endpoints = supervisors.endpoint_supervisor_client()
        endpoints.remove_group(lb.group.pk)
        # Remove key from config
        lb.group.environment.system.config_manager.delete(lb.config_key)
        lb.backend.delete_lb(lb)


model_signals.pre_delete.connect(LoadBalancer.pre_delete, sender=LoadBalancer)


class Host(AuditedModel):
    """
    Hosts can either be managed or unmanaged. Managed hosts are created when a
    group is scaled, but unmanaged hosts have no parent group since they are
    created and provisioned manually.
    """
    fqdn = models.TextField(unique=True)
    name = models.TextField(unique=True)
    hostname = models.TextField()
    domain_name = models.TextField(null=True)
    environment = models.ForeignKey('Environment', related_name='hosts')
    address = models.GenericIPAddressField()

    @classmethod
    def create(cls, env, group):
        """
        Creates, provisions, and saves a new host.

        :Parameters:
          - `env`: the host's environment.
          - `group`: the host's group.
        """
        domain_name = env.system.domain_name
        hostname = utils.generate_random_hex(8)
        fqdn = '%s.%s' % (hostname, domain_name) if domain_name else hostname

        host = cls(fqdn=fqdn, name=fqdn, hostname=hostname,
                   domain_name=domain_name, environment=env, group=group)

        if not env.backend:
            raise exceptions.UndefinedBackend()
        host.address = env.backend.create_host(host)
        host.finish_provisioning()
        host.save()
        log.info('Creating new instance for host...')
        host.create_instance(group.node)

        return host

    @classmethod
    def create_unmanaged(cls, env, name, hostname, fqdn):
        host = cls(fqdn=fqdn, name=name, hostname=hostname,
                   domain_name=env.system.domain_name, environment=env)
        host.finish_provisioning()
        host.save()
        return host

    def pull_nodes(self, group_pool, release=None):
        [self.agent.pull(node, release) for node in self.nodes]

        for instance in self.instances.get():
            group_pool.spawn(instance.restart)

    def create_instance(self, node):
        Instance.create(self.environment, self, node)

    def sync(self):
        # Install dependencies
        log.info('Installing dependencies...')
        for _ in xrange(10):
            result = self._call('state.highstate')
            if result != {}:
                log.debug(result)
                break
        # Synchronize modules
        log.info('Synchronizing modules...')
        for _ in xrange(10):
            result = self._call('saltutil.sync_modules')
            if result != {}:
                log.debug(result)
                break

    def finish_provisioning(self):
        self._accept_key()
        self.sync()

    def _accept_key(self):
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

    def _delete_key(self):
        wheel_client().call_func('key.delete', match=self.fqdn)

    def _call(self, *args, **kwargs):
        return salt_client().cmd(self.fqdn, *args, **kwargs)

    @property
    def nodes(self):
        nodes = []
        for instance in self.instances.all():
            if instance.node not in nodes:
                nodes.append(instance.node)
        return nodes

    @property
    @utils.memoized
    def agent(self):
        return AgentClient(self.address)

    @classmethod
    def pre_delete(cls, sender, instance, **kwargs):
        host = instance
        host._delete_key()
        if host.group:
            if not host.environment.backend:
                raise exceptions.UndefinedBackend()
            host.environment.backend.delete_host(host)
        else:
            host.environment.system.config_manager.remove_managed_host(host)


model_signals.pre_delete.connect(Host.pre_delete, sender=Host)


class Group(AuditedModel):
    """
    A group is a collection of homogeneous hosts. Each host in a group runs one
    instance that runs the the node associated with the group.
    """
    name = models.TextField(validators=[alphanumeric])
    environment = models.ForeignKey('Environment', related_name='groups')
    minimum_nodes = models.IntegerField(default=1)
    maximum_nodes = models.IntegerField(null=True)
    node = models.ForeignKey('Node')
    load_balancer = models.OneToOneField('LoadBalancer', null=True,
                                         related_name='group')
    unique_together = ('environment', 'name')

    def scale_up(self, amount):
        self._check_valid_amount(self.hosts.count() + amount)
        group(self._create_host.s() for _ in xrange(amount))().get()

    def scale_down(self, amount):
        self._check_valid_amount(self.hosts.count() - amount)
        hosts = self.hosts.all()[0:amount]
        group(self._delete_host.s(host.pk) for host in hosts)().get()

    def scale_to(self, amount):
        relative_amount = amount - self.hosts.count()
        if relative_amount > 0:
            self.scale_up(relative_amount)
        elif relative_amount < 0:
            self.scale_down(-relative_amount)

    def create_load_balancer(self, port_name, protocol, options={}):
        if not self.load_balancer:
            self.load_balancer = LoadBalancer.create(group=self,
                port_name=port_name, protocol=protocol, options=options)
        else:
            raise Exception('group already has a load balancer')

    def _check_valid_amount(self, amount):
        if self.maximum_nodes == None:
            valid = amount >= self.minimum_nodes
        else:
            valid = self.minimum_nodes <= amount <= self.maximum_nodes
        if not valid:
            raise Exception('invalid scaling amount')

    @task
    def _create_host(self):
        Host.create(self.environment, self)

    @task
    def _delete_host(self, host_id):
        Host.objects.get(pk=host_id).delete()

    @property
    def config_key(self):
        return self.environment.system.config_manger.get_group_key(self)

    @property
    def batch_size(self):
        return min(int(math.ceil(self.instances.count() / 2.0)),
                   settings.STRETCH_BATCH_SIZE)


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
