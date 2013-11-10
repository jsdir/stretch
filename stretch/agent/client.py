import json
import time
import requests
import time
from urlparse import urljoin
from django.conf import settings
from gevent import monkey
monkey.patch_all()


class AgentClient(object):
    def __init__(self, host, port=settings.STRETCH_AGENT_PORT):
        self.base_url = 'https://%s:%s' % (host, port)

    def add_node(self, node):
        requests.post(self.get_url('nodes'), data={'id': str(node.pk)})

    def remove_node(self, node):
        requests.delete(self.get_url('nodes/%s' % str(node.pk)))

    def pull(self, node, sha=None):
        env = self.host.environment
        ports = dict([(port.name, port.number) for port in node.ports.all()])
        if sha:
            app_path = None
        else:
            app_path = env.app_paths[node.name]

        task = self.run_task('nodes/%s' % str(node.pk), 'pull', {
            'sha': sha,
            'app_path': app_path,
            'ports': json.dumps(ports),
            'env_id': str(env.pk),
            'env_name': env.name,
            'image': node.get_image(local=True, private=True)
        })

    def add_instance(self, instance):
        requests.post(self.get_url('instances'), data={
            'id': str(instance.pk),
            'node_id': str(instance.node.pk),
            'host_name': instance.host.name,
            'config_key': instance.config_key
        })

    def remove_instance(self, instance):
        requests.delete(self.get_url('instances/%s' % str(isntance.pk)))

    def reload_instance(self, instance):
        task = self.run_task('instances/%s' % str(isntance.pk), 'reload')

    def restart_instance(self, instance):
        task = self.run_task('instances/%s' % str(isntance.pk), 'restart')

    def run_task(self, resource, task_name, options={}):
        base_url = self.get_url(urljoin(resource, 'tasks'))
        task_id = requests.post(base_url, data=options)['_id']

        while True:
            gevent.sleep(1.0)
            task = requests.get(urljoin(base_url, task_id)).json()
            if task['status'] == 'FAILED':
                raise Exception(task['error'])
            elif task['status'] == 'FINISHED':
                break

    def get_url(self, resource):
        return urljoin(self.base_url, 'v1', resource)
