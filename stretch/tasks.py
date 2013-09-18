from celery import task

from stretch import models


@task
def create_release_from_sources(system_name, sources):
    system = models.System.objects.get(name=system_name)
    release = models.Release.create_from_sources(system, sources)
