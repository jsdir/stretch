import os
import pyrax
import logging
from fabric.api import run, env, put, cd
from fabric.contrib.files import upload_template
from django.conf import settings

import stretch
#from stretch.salt_api import caller_client
#from stretch.agent.objects import LoadBalancer
from stretch import utils


log = logging.getLogger('stretch')


class Backend(object):
    def __init__(self, options):
        self.options = options
        self.autoloads = False
        self.store_images = options.get('store_images', True)
        # TODO: add in docs that delete_unused_images only happens when
        # store_images is set and a new image is created
        self.delete_unused_images = options.get('delete_unused_images', True)

    def create_host(self, host):
        raise NotImplementedError

    def delete_host(self, host):
        raise NotImplementedError

    def lb_add_endpoint(self, lb, host, port):
        raise NotImplementedError

    def lb_remove_endpoint(self, lb, host, port):
        raise NotImplementedError

    def create_lb(self, lb, hosts):
        raise NotImplementedError

    def delete_lb(self, lb):
        raise NotImplementedError

    def require_option(self, name):
        value = self.options.get(name)
        if not value:
            raise Exception('option "%s" does not exist in backend settings'
                            % name)
        return value


def get_image_name():
    prefix = settings.STRETCH_BACKEND_IMAGE_PREFIX
    return '%s-%s' % (prefix, stretch.__version__), prefix


def get_backend(env):
    backend_map = get_backend_map(settings.STRETCH_BACKENDS)
    return backend_map.get(env.system.name, {}).get(env.name)


@utils.memoized
def get_backend_map(backend_dict):
    backend_map = {}

    for system_name, envs in backend_dict.iteritems():
        backend_map[system_name] = {}
        for env_name, backends in envs.iteritems():
            for class_name, options in backends.iteritems():
                # Only one backend per environment
                backend_class = utils.get_class(class_name)
                backend_map[system_name][env_name] = backend_class(options)
                break

    return backend_map
