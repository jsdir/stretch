import json

from django.http import HttpResponse, HttpResponseNotFound


def get_releases(request, system_name):
    release_tag = request.GET.get('tag')

    system = System.find(name=system_name)
    if not system:
        return HttpResponseNotFound()

    release = system.releases.find(tag=release_tag)
    if not release:
        return HttpResponseNotFound()

    return HttpResponse(json.dumps({
        'id': release.pk
    }), mimetype='application/json')


def deploy(system_name):
    tasks.deploy().delay()
    return # celery task id
