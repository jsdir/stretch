import os
import logging
import tarfile
import json
import time
from distutils import dir_util
import jsonfield
import uuidfield
from django.db import models
from django.dispatch import receiver
from django.core.validators import RegexValidator
from django.conf import settings
from celery import current_task, group
from celery.contrib.methods import task

from stretch import signals, sources, utils, backends, parser
from stretch.salt_api import salt_client, wheel_client, runner_client


log = logging.getLogger('stretch')
alphanumeric = RegexValidator(r'^[a-zA-Z0-9_\-]*$',
    'Only alphanumeric characters, underscores, and hyphens are allowed.')


class AuditedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Service(models.Model):
    name = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='services')
    data = jsonfield.JSONField()
    unique_together = ('system', 'name')


class System(AuditedModel):
    name = models.TextField(unique=True, validators=[alphanumeric])
    domain_name = models.TextField(unique=True, null=True)

    def create_release(self, options):
        return Release.create(self.source.pull(options), system=self)

    def load_sources(self):
        if (hasattr(self.source, 'autoload') and self.source.autoload):
            for env in self.environments.all():
                if env.has_autoloading_backend():
                    env.deploy.delay(self.source)
                else:
                    log.debug('Backend does not autoload. Skipping.')

    @property
    def source(self):
        # Only one source is used per system for now
        if not hasattr(self, '_source'):
            system_sources = sources.get_sources(self)
            if system_sources:
                self._source = system_sources[0]
            else:
                raise Exception('no source defined for this system')
        return self._source


class Environment(AuditedModel):
    name = models.TextField(validators=[alphanumeric])
    auto_deploy = models.BooleanField(default=False)
    system = models.ForeignKey('System', related_name='environments')
    current_release = models.ForeignKey('Release', null=True)
    using_source = models.BooleanField(default=False)

    @property
    def backend(self):
        if not hasattr(self, '_backend'):
            self._backend = backends.get_backend(self)
        return self._backend

    # TODO: make tasks non-concurrent
    @task
    def deploy(self, obj):
        log.info('Deploying %s to %s/%s' % (obj, self.system.name, self.name))

        total_steps = 7

        def update_status(current_step, description):
            log.info(description)
            current_task.update_state(state='PROGRESS',
                meta={
                    'description': description,
                    'current': current_step,
                    'total': total_steps
                }
            )

        existing_release = self.current_release
        deploy = Deploy.create(
            environment=self,
            existing_release=existing_release,
            task_id=current_task.request.id
        )

        if isinstance(obj, sources.Source):
            is_release = False
        elif isinstance(obj, Release):
            is_release = True
            deploy.release = obj
        else:
            raise Exception('cannot deploy object "%s"' % obj)

        log.info('Saving deploy')
        deploy.save()
        log.info('Finished saving deploy')

        # Pull release
        update_status(1, 'Pulling release')

        if is_release:
            deploy.snapshot = obj.get_snapshot()
            release_config = obj.get_config()
            if existing_release:
                deploy.existing_snapshot = existing_release.get_snapshot()
        else:
            deploy.snapshot = parser.Snapshot(utils.tmp_dir(obj.pull()))
            release_config = deploy.snapshot.get_config()

        snapshot = deploy.snapshot

        update_status(2, 'Running build plugins')
        snapshot.run_build_plugins(deploy)

        update_status(3, 'Running pre-deploy plugins')
        snapshot.run_pre_deploy_plugins(deploy)

        # Deploy to backend
        update_status(4, 'Deploying to backend...')

        # Build images and save config if source deploy
        if not is_release:
            snapshot.build_and_push(None, self)
            config_path = self.get_config_path()
            utils.makedirs(os.path.split(config_path)[0])
            snapshot.save_config(config_path)
            # TODO: Start node piping

        # TODO: Mount templates, use environment subdirectory to prevent clash
        
        def callback(instance):
            # TODO: share registry url, batch_size
            if is_release:
                instance.deploy(obj.sha)
            else:
                instance.deploy()

        self.map_instances(callback)

        # TODO: Unmount templates

        update_status(5, 'Running post-deploy plugins')
        deploy.snapshot.run_post_deploy_plugins(deploy)

        # Delete temporary directories
        update_status(6, 'Cleaning up')

        utils.delete_path(snapshot.path)
        if deploy.existing_snapshot:
            utils.delete_path(deploy.existing_snapshot.path)

        # Update current release
        update_status(7, 'Setting new release')

        self.using_source = not is_release

        if is_release:
            self.current_release = obj
        else:
            self.current_release = None

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
                instance.reload(remember=False)

    def has_autoloading_backend(self):
        return isinstance(self.backend, backends.AutoloadingBackend)


    def get_config_path(self):
        return os.path.join(settings.STRETCH_DATA_DIR, 'environments',
                            str(self.pk), 'config.json')

    def update_config(self):
        config_data = None
        if self.current_release:
            config_data = self.current_release.get_config()
        elif self.using_source:
            config_data = json.load(open(self.get_config_path()))

        if config_data:
            # Use stub deploy
            deploy = Deploy.create(environment=self)
            rendered_config = parser.render_config(config_data, deploy)

            def callback(instance):
                config = rendered_config.get(instance.node.name)
                if config:
                    instance.load_config(config)
                instance.restart()

            self.map_instances(callback)

    def map_instances(self, callback):
        instance_count = self.instances.count()
        batch_size = min(instance_count / 2, settings.STRETCH_BATCH_SIZE)

        remaining = list(self.instances.all())
        pending = []

        while remaining or pending:
            while len(pending) < instance_count and remaining:
                instance = remaining.pop()
                instance.deactivate()
                callback(instance)
                pending.append(instance)

            time.sleep(0.5)

            for instance in pending:
                if instance.jobs_finished():
                    instance.activate()
                    pending.remove(instance)

        # TODO: Do simultaneously with node types (instance.node)


class Release(AuditedModel):
    name = models.TextField()
    sha = models.CharField('SHA', max_length=40)
    system = models.ForeignKey('System', related_name='releases')
    unique_together = ('system', 'name', 'sha')

    @classmethod
    def create(cls, path, system):
        release = cls(
            name=utils.generate_memorable_name(),
            sha=utils.generate_random_hex(40),
            system=system
        )

        # Copy to temporary directory
        tmp_path = utils.tmp_dir(path)

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

        # Dump release configuration
        snapshot.save_config(os.path.join(release_dir, 'config.json'))

        # Build docker images
        snapshot.build_and_push(release)

        # Delete snapshot buffer
        utils.delete_path(tmp_path)

        # Build finished
        release.save()
        signals.release_created.send(sender=release)
        return release

    def get_snapshot(self):
        tar_path = os.path.join(self.get_data_dir(), 'snapshot.tar.gz')
        tmp_path = utils.tmp_dir()
        tar_file = tarfile.open(tar_path)
        tar_file.extractall(tmp_path)
        tar_file.close()
        return parser.Snapshot(tmp_path)

    def get_config(self):
        config_path = os.path.join(self.get_data_dir(), 'config.json')
        with open(config_path) as config_file:
            return json.loads(config_file.read())

    def get_data_dir(self):
        return os.path.join(settings.STRETCH_DATA_DIR, 'releases', self.sha)


class Node(AuditedModel):
    name = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='nodes')
    ports = jsonfield.JSONField()
    unique_together = ('system', 'name')


class PortBinding(AuditedModel):
    instance = models.ForeignKey('Instance', related_name='port_bindings')
    source = models.IntegerField()
    destination = models.IntegerField()


class Instance(AuditedModel):
    # UUIDs are used for instances because the instance ids are included in
    # the application context
    id = uuidfield.UUIDField(auto=True, primary_key=True)

    environment = models.ForeignKey('Environment', related_name='instances')
    host = models.ForeignKey('Host', related_name='instances')
    node = models.ForeignKey('Node', related_name='instances')

    @classmethod
    def create(cls, *args, **kwargs):
        instance = cls(*args, **kwargs)
        instance.save()

        # TODO: deal with port conflicts
        instance_ports = []
        for port in instance.node.ports:
            instance_ports.append((port, port))
            binding = PortBinding(source=port, destination=port,
                                  instance=instance)
            binding.save()

        instance.call('stretch.add_instance', instance_ports)
        return instance

    def delete(self):
        self.call('stretch.remove_instance')
        super(Instance, self).delete()

    @property
    def pending_jobs(self):
        if not hasattr(self, '_pending_jobs'):
            self._pending_jobs = []
        return self._pending_jobs

    def reload(self, **kwargs):
        self.call('stretch.reload', **kwargs)

    def restart(self, **kwargs):
        self.call('stretch.restart', **kwargs)

    def load_config(self, config, **kwargs):
        self.call('stretch.load_config', config, **kwargs)

    def deploy(self, sha=None, **kwargs):
        self.call('stretch.deploy', sha, **kwargs)

    def activate(self):
        if self.host.group:
            self.host.group.activate(self.host)

    def deactivate(self):
        if self.host.group:
            self.host.group.deactivate(self.host)

    def call(self, *args, **kwargs):
        kwargs['instance_id'] = str(self.pk)
        kwargs['node_id'] = str(self.node.pk)

        jid = salt_client().cmd_async(self.host.fqdn, *args, **kwargs)

        if kwargs.pop('remember', True):
            self.pending_jobs.append(jid)

        return jid

    def jobs_finished(self):
        active_jobs = runner_client().cmd('jobs.active', []).keys()

        for jid in self.pending_jobs:
            if jid in active_jobs:
                return False
            else:
                self.pending_jobs.remove(jid)

        return True


class LoadBalancer(models.Model):
    port = models.IntegerField()
    host_port = models.IntegerField()
    protocol = models.TextField()
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
    domain_name = models.TextField()
    group = models.ForeignKey('Group', related_name='hosts', null=True)
    environment = models.ForeignKey('Environment', related_name='hosts')
    address = models.GenericIPAddressField()

    @classmethod
    def create(cls, env, group=None):
        domain_name = env.system.domain_name

        hostname = (utils.generate_random_hex(8) if group
                    else fqdn.replace(domain_name, ''))
        fqdn = '%s.%s' % (hostname, domain_name) if domain_name else hostname

        host = cls(fqdn=fqdn, hostname=hostname, domain_name=domain_name,
                   environment=env, group=group)

        if group:
            if not env.backend:
                raise Exception('no backend defined') # TODO: common specific exceptions
            host.address = env.backend.create_host(host)

        host.finish_provisioning()
        host.save()

        if group:
            Instance.create(environment=host.environment, host=host,
                            node=host.group.node)

        return host

    def delete(self):
        self.delete_key()
        if self.group:
            if not self.environment.backend:
                raise Exception('no backend defined') # TODO: common specific exceptions
            self.environment.backend.delete_host(self)
        super(Host, self).delete()

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
        self.call_salt('state.highstate')
        # Synchronize modules
        log.info('Synchronizing modules...')
        self.call_salt('saltutil.sync_all')

    def call_salt(self, *args, **kwargs):
        salt_client().cmd(self.fqdn, *args, **kwargs)


class Group(AuditedModel):
    name = models.TextField(validators=[alphanumeric])
    environment = models.ForeignKey('Environment', related_name='groups')
    minimum_nodes = models.IntegerField(default=1)
    maximum_nodes = models.IntegerField(null=True)
    node = models.ForeignKey('Node')
    load_balancer = models.OneToOneField('LoadBalancer', null=True)
    unique_together = ('environment', 'name')

    def activate(self, host):
        if self.load_balancer:
            self.load_balancer.activate_host(host)

    def deactivate(self, host):
        if self.load_balancer:
            self.load_balancer.deactivate_host(host)

    def scale_up(self, amount):
        self.check_valid_amount(self.host_count + amount)
        group(self.create_host.s() for _ in xrange(amount))().get()
        self.environment.update_config()

    def scale_down(self, amount):
        self.check_valid_amount(self.host_count - amount)

        hosts = self.hosts.all()[0:amount]

        for host in hosts:
            host.group = None
            host.save()

        self.environment.update_config()
        group(self.delete_host.s(host.pk) for host in hosts)().get()

    def create_load_balancer(self, port, host_port, protocol):
        if not self.load_balancer and self.host_count > 0:
            self.load_balancer = LoadBalancer(port=port, host_port=host_port,
                                              protocol=protocol)
            self.load_balancer.activate_with_hosts(self.hosts.all())
            self.load_balancer.save()

    def scale_to(self, amount):
        relative_amount = amount - self.host_count
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
    def create_host(self):
        host = Host.create(self.environment, self)
        if self.load_balancer:
            self.load_balancer.add_host(host)

    @task
    def delete_host(self, host_id):
        host = Host.get(pk=host_id)
        if self.load_balancer:
            self.load_balancer.remove_host(host)
        host.delete()

    @property
    def host_count(self):
        return self.hosts.count()

    # TODO: delete chaining for host, group, instance, env, system


class Deploy(AuditedModel):
    release = models.ForeignKey('Release', related_name='deploy_releases',
                                null=True)
    existing_release = models.ForeignKey('Release',
        related_name='deploy_existing_releases', null=True)
    environment = models.ForeignKey('Environment', related_name='deploys')
    task_id = models.CharField(max_length=128)

    @classmethod
    def create(cls, *args, **kwargs):
        deploy = cls(*args, **kwargs)
        deploy.snapshot = None
        deploy.existing_snapshot = None
        return deploy

    def is_from_release(self):
        return bool(release)


@receiver(signals.sync_source)
def on_sync_source(sender, snapshot, nodes, **kwargs):
    source = sender
    log.info('Source %s changed' % source)
    log.info('Changed nodes: %s' % nodes)
    system_name = sources.get_system(source)
    if system_name:
        system = System.objects.get(name=system_name)
        for env in system.environments.all():
            if env.has_autoloading_backend():
                env.autoload.delay(source, nodes)
            else:
                log.debug('Backend does not autoload. Skipping.')


@receiver(signals.load_sources)
def on_load_sources(sender, **kwargs):
    log.info('Deploying autoloadable sources...')
    for system in System.objects.all():
        system.load_sources()


@receiver(signals.release_created)
def on_release_created(sender, **kwargs):
    release = sender
    for env in release.system.environments.all():
        if env.auto_deploy:
            env.deploy.delay(self)
