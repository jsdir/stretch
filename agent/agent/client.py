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
        return self.call('node:add', str(node.pk))

    def remove_node(self, node):
        return self.call('node:remove', str(node.pk))

    def pull_node(self, node, env, release=None):
        ports = dict([(port.name, port.number) for port in node.ports.all()])

        if release:
            sha = release.sha
            app_path = None
            image = node.get_image(local=False, private=True)
        else:
            sha = None
            app_path = env.app_paths[node.name]
            image = node.get_image(local=True)

        return self.call('node:pull', str(node.pk), {
            'sha': sha,
            'app_path': app_path,
            'ports': json.dumps(ports),
            'env_id': str(env.pk),
            'env_name': env.name,
            'image': image
        })

    def add_instance(self, instance, host):
        return self.call('instance:add', str(instance.pk),
            str(instance.node.pk), host.name, instance.config_key)

    def remove_instance(self, instance):
        return self.call('instance:remove', str(instance.pk))

    def reload_instance(self, instance):
        return self.call('instance:reload', str(instance.pk))

    def restart_instance(self, instance):
        return self.call('instance:restart', str(instance.pk))

    def add_lb(self, lb):
        return self.call('lb:add', str(lb_id.pk))

    def remove_lb(self, lb):
        return self.call('lb:remove', str(lb_id.pk))

    def add_endpoint(self, lb, endpoint):
        return self.call('lb:add_endpoint', str(lb_id.pk), endpoint)

    def remove_endpoint(self, lb, endpoint):
        return self.call('lb:remove_endpoint', str(lb_id.pk), endpoint)
