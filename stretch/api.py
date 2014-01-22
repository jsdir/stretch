import json
import time
from django.http import HttpResponse, HttpResponseNotFound, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from stretch import models, tasks


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
