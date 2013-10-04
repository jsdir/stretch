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

from stretch import signals, sources, utils

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

    @property
    def backends(self):
        if not hasattr(self, '_backends'):
            self._backends = backends.get_backends(self)
        return self._backends

    @task
    def deploy(self, obj):
        log.info('Deploying %s to %s/%s' % (obj, self.system.name, self.name))
        if isinstance(obj, sources.Source):
            pass
        elif isinstance(obj, Release):
            pass
        # need: snapshot in sandbox and release configuration

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
    def create(cls, snapshot, system):
        release = cls(
            name=utils.generate_memorable_name(),
            sha=utils.generate_random_hex(40),
            system=system
        )

        # Build release from snapshot
        # Archive the release
        release_dir = os.path.join(settings.DATA_DIR, 'releases', release.sha)
        utils.clear_path(release_dir)

        # Tar release buffer
        tar_path = os.path.join(release_dir, '%s.tar.gz' % release.sha)
        tar_file = tarfile.open(tar_path, 'w:gz')
        tar_file.add(snapshot.path, '/')
        tar_file.close()

        # Write release configuration
        with open(os.path.join(release_dir, '%s.json' % release.sha), 'w') as f:
            f.write(json.dumps(snapshot.get_release_config()))

        # Build docker images
        snapshot.build_and_push(release)

        # Build finished
        release.save()
        signals.release_created.send(sender=release)
        return release


@receiver(signals.sync_source)
def on_sync_source(sender, snapshot, nodes, **kwargs):
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
