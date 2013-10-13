import os
import logging
import tarfile
import json
from distutils import dir_util
import uuidfield
from django.db import models
from django.dispatch import receiver
from django.core.validators import RegexValidator
from django.conf import settings
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


class System(AuditedModel):
    name = models.TextField(unique=True, validators=[alphanumeric])

    def create_release(self, options):
        return Release.create(self.source.pull(options), system=self)

    def load_sources(self):
        if (isinstance(self.source, sources.AutoloadableSource) and
                self.source.autoload):
            for env in self.environments.all():
                env.deploy.delay(self.source)

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
    current_release = models.ForeignKey('Release')
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
            task_id=current_task.task_id
        )

        if isinstance(obj, sources.Source):
            is_release = False
        elif isinstance(obj, Release):
            is_release = True
            deploy.release = obj
        else:
            raise Exception('cannot deploy object "%s"' % obj)

        deploy.save()

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

        remaining = self.instances.all()
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
        tmp_path = utils.tmp_dir(obj.pull())

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
        return os.path.join(settings.DATA_DIR, 'releases', self.sha)


class Node(AuditedModel):
    system = models.ForeignKey('System', related_name='nodes')
    name = models.TextField()
    unique_together = ('system', 'name')


class Instance(AuditedModel):
    # UUIDs are used for instances because the instance ids are included in
    # the application context
    id = uuidfield.UUIDField(auto=True, primary_key=True)

    environment = models.ForeignKey('Environment', related_name='instances')
    host = models.ForeignKey('Host', related_name='instances')
    node = models.ForeignKey('Node', related_name='instances')
    fqdn = models.TextField(unique=True)

    # TODO: port bindings

    @property
    def pending_jobs(self):
        if not hasattr(self, '_pending_jobs'):
            self._pending_jobs = []
        return self._pending_jobs

    def reload(self, **kwargs):
        self.call('reload', **kwargs)

    def restart(self, **kwargs):
        self.call('restart', **kwargs)

    def load_config(self, config, **kwargs):
        self.call('load_config', config, **kwargs)

    def deploy(self, sha=None, **kwargs):
        self.call('deploy', sha, **kwargs)

    def activate(self):
        group = self.host.group
        if group:
            group.activate(self.host)

    def deactivate(self):
        group = self.host.group
        if group:
            group.deactivate(self.host)

    def call(self, cmd, *args, **kwargs):
        jid = salt_client().cmd_async(self.fqdn, cmd, *args, **kwargs,
                                      node_id=str(self.node.pk))

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
    ip = models.GenericIPAddressField()
    backend_id = models.CharField(max_length=32, unique=True)

    @classmethod
    def create(cls, group, port, host_port, protocol, hosts):
        lb = cls(group=group, port=port, host_port=host_port,
                 protocol=protocol)
        lb.backend_id, lb.ip = lb.get_backend().create_lb(self, hosts)
        return lb

    def get_backend(self):
        return self.group.environment.backend

    def add_host(self, host):
        self.get_backend().add_to_lb(self.backend_id, host)

    def remove_host(self, host):
        self.get_backend().remove_from_lb(self.backend_id, host)

    def activate_host(self, host):
        self.get_backend().activate_host(self.backend_id, host)

    def deactivate_host(self, host):
        self.get_backend().deactivate_host(self.backend_id, host)

    def delete(self):
        self.get_backend().delete_lb(self.backend_id)
        super(LoadBalancer, self).delete()


class Group(AuditedModel):
    name = models.TextField(unique=True)
    environment = models.ForeignKey('Environment', related_name='groups')
    load_balancer = models.OneToOneField('LoadBalancer')
    unique_together = ('environment', 'name')

    def activate(self, host):
        if self.load_balancer:
            self.load_balancer.activate_host(host)

    def deactivate(self, host):
        if self.load_balancer:
            self.load_balancer.deactivate_host(host)


class Host(AuditedModel):
    group = models.ForeignKey('Group', related_name='hosts')
    environment = models.ForeignKey('Environment', related_name='hosts')
    # TODO: managed/unmanaged
    # TODO: refactor original model


class Deploy(AuditedModel):
    release = models.ForeignKey('Release')
    existing_release = models.ForeignKey('Release')
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
    # TODO: is snapshot needed?
    source = sender
    log.info('Source %s changed' % source)
    log.info('Changed nodes: %s' % nodes)
    system_name = sources.get_system(source)
    if system_name:
        system = System.objects.get(name=system_name)
        for env in system.environments.all():
            env.autoload.delay(source, nodes)


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
