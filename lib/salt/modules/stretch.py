import os
import errno
import docker
from subprocess import call

# On startup
# Go through instance database and run

docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.4')
agent_dir = '/var/lib/stretch/agent'


class Container(object):
    def __init__(self, instance_id):
        pass

    def restart(self):
        pass


class Instance(object):
    def __init__(self, instance_id):
        self.id = instance_id

    def restart(self):
        pass


def add_instance(instance_id, node_id, node_name, environment_id, ports):
    # Add instance to global instance table
    # Initialize instance
    pass


def remove_instance(instance_id):
    # Stop instance
    # Remove <Instance> to global instance table
    pass


def reload():
    pass


def restart():
    pass


def load_config(config, instance_id):
    # Relate config with instance_id
    pass


def deploy(sha, instance_id):
    if sha:
        # TODO: deploy with release sha
    else:
        # TODO: Deploy with local image with self.node.pk/name
    # images with sha need to be pulled, first pull sets a lock,
    # subsequent pulls wait for lock and use the newly-pulled images


def pull(options):
    release_sha = options.get('release_sha')
    release_name = options.get('release_name')
    registry_url = options.get('registry_url')
    config = release.get('config')

    # (along with templates from the fileserver)
    # Pull to template directory
    path = os.path.join('salt://templates', templates_path)
    __salt__['cp.get_dir'](path, dest)

    # Pull release image for every node under the agent/system

    for node in _collected_nodes():
        image = '%s/%s/%s:%s' % (registry_url, system_id, node_type,
                                 release_sha)
        docker_client.pull(image)

        # Save image_path to cache file or state


def deploy(instance_id, release_sha, environment_id, environment_name):
    container = Container(instance) # get instance_id
    # docker stop container.id
    # docker run tag -ports -mount rendered templates


def autoload_deploy(options):
    # This is a deploy without the release
    config = options.config
    environment = options.environment

    for instance.environment == environment:
        # apply templates



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
