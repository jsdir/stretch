import json
from django.http import HttpResponse, HttpResponseNotFound, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from stretch import models, tasks


def index_releases(request, system_name):
    release_tag = request.GET.get('tag')

    system = _get_system(system_name)
    release = _get_release(release_tag)

    return HttpResponse(json.dumps({
        'id': release.pk
    }), mimetype='application/json')


@csrf_exempt
def create_release(request, system_name):
    options = request.POST.get('options')

    system = _get_system(system_name)
    release = system.create_release(options)

    return HttpResponse(json.dumps({
        'id': release.pk
    }), mimetype='application/json')


@csrf_exempt
def deploy(request, system_name, env_name):
    release_id = request.POST.get('release_id')

    release = models.Release.find(release_id)
    if not release:
        return HttpResponseNotFound()

    task = env.deploy.delay(release)
    return StreamingHttpResponse(stream_response_generator(task))


def stream_response_generator(task):
    task.get()
    yield


def _get_system(system_name):
    system = models.System.find(name=system_name)
    if not system:
        raise HttpResponseNotFound()


def _get_release(release_tag):
    release = models.Release.find(tag=release_tag)
    if not release: # TODO
        raise HttpResponseNotFound()
