import json
import requests
from urlparse import urljoin
from django.conf import settings
import gevent
# TODO: patch networking IO


class AgentClient(object):
    def __init__(self, host):
        self.host = host
        self.cert = settings.STRETCH_AGENT_CERT
        self.base_url = 'https://%s:%s' % (host.address,
                                           settings.STRETCH_AGENT_PORT)

    def add_node(self, node):
        requests.post(self.get_url('nodes'), data={'id': str(node.pk)},
                      cert=self.cert)

    def remove_node(self, node):
        requests.delete(self.get_url('nodes/%s' % str(node.pk)),
                        cert=self.cert)

    def pull(self, node, release=None):
        env = self.host.environment
        ports = dict([(port.name, port.number) for port in node.ports.all()])
        if release:
            sha = release.sha
            app_path = None
            image = node.get_image(local=False, private=True)
        else:
            sha = None
            app_path = env.app_paths[node.name]
            image = node.get_image(local=True)

        task = self.run_task('nodes/%s' % node.pk, 'pull', {
            'sha': sha,
            'app_path': app_path,
            'ports': json.dumps(ports),
            'env_id': str(env.pk),
            'env_name': env.name,
            'image': image
        })

    def add_instance(self, instance):
        requests.post(self.get_url('instances'), data={
            'id': str(instance.pk),
            'node_id': str(instance.node.pk),
            'host_name': instance.host.name,
            'config_key': instance.config_key
        }, cert=self.cert)

    def remove_instance(self, instance):
        requests.delete(self.get_url('instances/%s' % str(instance.pk)),
                        cert=self.cert)

    def reload_instance(self, instance):
        task = self.run_task('instances/%s' % str(instance.pk), 'reload')

    def restart_instance(self, instance):
        task = self.run_task('instances/%s' % str(instance.pk), 'restart')

    def run_task(self, resource, task_name, options={}):
        url = self.get_url('/'.join([resource, 'tasks']))
        task_id = requests.post(url, data=options, cert=self.cert).json()['id']
        task_url = self.get_url('/'.join(['tasks', task_id]))

        while self.task_running(task_url):
            gevent.sleep(1.0)

    def task_running(self, task_url):
        task = requests.get(task_url, cert=self.cert).json()
        if task['status'] == 'FAILED':
            raise Exception(task['error'])
        elif task['status'] == 'FINISHED':
            return False
        else:
            return True

    def get_url(self, resource):
        return urljoin(self.base_url, 'v1/' + resource)
