import json
from django.http import HttpResponse, HttpResponseNotFound, StreamingHttpResponse

from stretch import models


def index_releases(request, system_name):
    release_tag = request.GET.get('tag')

    system = models.System.find(name=system_name)
    if not system:
        return HttpResponseNotFound()

    release = system.releases.find(tag=release_tag)
    if not release:
        return HttpResponseNotFound()

    return HttpResponse(json.dumps({
        'id': release_tag #release.pk
    }), mimetype='application/json')


def deploy(request, system_name, env_name):
    release_id = request.POST.get('release_id')

    release = models.Release.find(release_id)
    if not release:
        return HttpResponseNotFound()

    tasks.deploy().delay()

    return StreamingHttpResponse(stream_response_generator())


def stream_response_generator():
    for x in range(1,11):
        yield 'Log entry {}\n'.format(x)
        time.sleep(.2)
