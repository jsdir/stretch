import json
from django.http import (HttpResponse, HttpResponseNotFound,
                         StreamingHttpResponse, Http404)
from django.views.decorators.csrf import csrf_exempt

from stretch import models, tasks


@csrf_exempt
def release(request, system_name):
    if request.method == 'GET':
        release_tag = request.GET.get('tag')

        system = _get_system(system_name)
        release = _get_release(release_tag)

        return HttpResponse(json.dumps({
            'id': release.pk
        }), mimetype='application/json')

    elif request.method == 'POST':  # pragma: no branch
        options = json.loads(request.POST['options'])

        system = _get_system(system_name)
        release = system.create_release(options)

        return HttpResponse(json.dumps({
            'id': release.pk
        }), mimetype='application/json')


@csrf_exempt
def deploy(request, system_name, env_name):
    release_id = request.POST.get('release_id')
    system = _get_system(system_name)

    try:
        env = system.environments.get(name=env_name)
    except models.Environment.DoesNotExist:
        raise Http404()

    try:
        release = models.Release.objects.get(pk=release_id)
    except models.Release.DoesNotExist:
        raise Http404()

    task = env.deploy.delay(release)
    return StreamingHttpResponse(stream_response_generator(task))


def stream_response_generator(task):
    task.get()
    yield


def _get_system(system_name):
    try:
        return models.System.objects.get(name=system_name)
    except models.System.DoesNotExist:
        raise Http404()


def _get_release(release_tag):
    try:
        return models.Release.objects.get(tag=release_tag)
    except models.Release.DoesNotExist:
        raise Http404()
