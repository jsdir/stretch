import os
import errno
import docker


docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.4')
agent_dir = '/var/lib/stretch/agent'

def create_node(id, node_type):
    pass


def delete_node(id):
    pass


def pull(release_sha, registry_url, system_name, templates_path):
    # ()along with templates from the fileserver)
    path = os.path.join('salt://templates', templates_path)
    __salt__['cp.get_dir'](path, dest)

    # Pull release image for every node under the agent/system

    for node in _collected_nodes():
        image = '%s/%s/%s:%s' % (registry_url, system_name, node_type,
                                 release_sha)
        docker_client.pull(image)

        # Save image_path to cache file or state


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise
