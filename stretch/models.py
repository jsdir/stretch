import os
import logging
import tarfile
import json
from distutils import dir_util
from django.db import models
from django.dispatch import receiver
from django.core.validators import RegexValidator
from django.conf import settings
from celery.contrib.methods import task

from stretch import signals, sources, utils, backends, parser

log = logging.getLogger('stretch')
alphanumeric = RegexValidator(r'^[a-zA-Z0-9_\-]*$',
    'Only alphanumeric characters, underscores, and hyphens are allowed.')


class AuditedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        abstract = True


class System(models.Model):
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


class Environment(models.Model):
    name = models.TextField(validators=[alphanumeric])
    auto_deploy = models.BooleanField(default=False)
    system = models.ForeignKey('System', related_name='environments')
    current_release = models.ForeignKey('Release')

    @property
    def backend(self):
        if not hasattr(self, '_backend'):
            self._backend = backends.get_backend(self)
        return self._backend

    @task
    def deploy(self, obj):
        log.info('Deploying %s to %s/%s' % (obj, self.system.name, self.name))

        total_steps = 8

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
        deploy.snapshot.run_build_plugins(deploy)

        update_status(3, 'Running pre-deploy plugins')
        deploy.snapshot.run_pre_deploy_plugins(deploy)

        update_status(4, 'Running post-deploy plugins')
        deploy.snapshot.run_post_deploy_plugins(deploy)

        # Delete temporary directories
        update_status(5, 'Cleaning up')

        utils.delete_path(snapshot.path)
        if deploy.existing_snapshot:
            utils.delete_path(deploy.existing_snapshot.path)

        # Update current release
        update_status(6, 'Setting new release')

        if is_release:
            self.current_release = obj
        else:
            self.current_release = None
        self.save()

    @task
    def autoload(self, source, nodes):
        log.info('Autoloading %s' % source)
        source.run_build_plugins(self, nodes)
        source.run_pre_deploy_plugins(self, nodes)
        source.run_post_deploy_plugins(self, nodes)


class Release(AuditedModel):
    name = models.TextField()
    sha = models.CharField('SHA', max_length=40)
    system = models.ForeignKey('System', related_name='releases')
    unique_together = ('name', 'system')

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

        # Write release configuration
        with open(os.path.join(release_dir, 'config.json'), 'w') as f:
            f.write(json.dumps(snapshot.get_release_config()))

        # Build docker images
        snapshot.build_and_push(release)

        # Remove snapshot buffer
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


class Deploy(AuditedModel):
    release = models.ForeignKey('Release')
    existing_release = models.ForeignKey('Release')
    environment = models.ForeignKey('Environment')
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
