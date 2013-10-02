#from __future__ import absolute_import
from celery import task

#import stretch
import stretch
print dir(stretch)
from stretch.models import System, Release


@task
def create_release_from_sources(system_name, source_options):
    system = System.objects.get(name=system_name)
    release = Release(system, source_options)


@task
def create_host(group):
    host = stretch.backend.create_host()
    host.parent = group
    host.save()
    if group.load_balancer:
        group.load_balancer.add_host(host)


@task
def remove_host(host):
    if group.load_balancer:
        group.load_balancer.remove_host(host)
    stretch.backend.delete_host(host)
    host.delete()
