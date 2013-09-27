import os
import errno
import docker
from subprocess import call


docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.4')
agent_dir = '/var/lib/stretch/agent'


class Container(object):
    def __init__(self, instance_id):
        pass

    def restart(self):
        pass


def add_instance(instance_id, node_name, ports):
    pass


def remove_instance(instance_id):
    pass


def pull(release_sha, registry_url, system_name, templates_path):
    # (along with templates from the fileserver)
    path = os.path.join('salt://templates', templates_path)
    __salt__['cp.get_dir'](path, dest)

    # Pull release image for every node under the agent/system

    for node in _collected_nodes():
        image = '%s/%s/%s:%s' % (registry_url, system_name, node_type,
                                 release_sha)
        docker_client.pull(image)

        # Save image_path to cache file or state

def autoload(instance_id, app_path):
    # Check for user-defined autoload.sh
    # TODO: In a newer release, docker will have functionality to run
    #       a command inside a running container. This will remove
    #       dependency of lxc-attach.
    container = Container(instance_id)
    autoload_file = '/usr/share/stretch/autoload.sh'
    code = call(['lxc-attach', '-n', container.id, '--', '/bin/bash',
                 autoload_file])
    if code == 3:
        # No user-defined autoload.sh, restart container
        container.restart()

def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
