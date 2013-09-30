from celery import task, models


@task
def create_release_from_sources(system_name, source_options):
    system = models.System.objects.get(name=system_name)
    release = models.Release(system, source_options)
