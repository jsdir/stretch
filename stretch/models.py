import logging
from django.db import models
from django.dispatch import receiver
from celery.contrib.methods import task

from stretch import signals, sources, utils

log = logging.getLogger('stretch')
alphanumeric = RegexValidator(r'^[a-zA-Z0-9_\-]*$',
    'Only alphanumeric characters, underscores, and hyphens are allowed.')


class System(models.Model):
    name = models.TextField(unique=True, validators=[alphanumeric])

    def create_release(self, options):
        release = Release.create(self.source.pull(options), system=self)
        release.save()
        return release

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


class Release(models.Model):
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

        release.build_from(path)
        release.save()

        for env in release.system.environments.all():
            if env.auto_deploy:
                env.deploy.delay(self)

    def build_from(self, path):
        pass


@receiver(signals.source_changed)
def on_source_changed(sender, changed_files, **kwargs):
    source = sender
    log.info('Source %s changed' % source)
    log.info('Changed files: %s' % changed_files)
    system_name = sources.get_system(source)
    if system_name:
        system = System.objects.get(name=system_name)
        [env.deploy.delay(source) for env in system.environments.all()]
