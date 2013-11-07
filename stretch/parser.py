import os
import sys
import yaml
import json
import collections
import gnupg
import docker
import logging
from distutils import dir_util
from django.conf import settings
from StringIO import StringIO
from contextlib import contextmanager

from stretch import utils, contexts, exceptions
from stretch.plugins import create_plugin


log = logging.getLogger('stretch')
docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.4')


# TODO: container build errors need to stop build, output from builds needs to
# be streamed along with plugin output.
class Snapshot(object):
    def __init__(self, path):
        self.path = path
        self.relative_path = '/'
        self.nodes = []
        self.containers = []

        # Begin parsing source
        self.parse()
        self.plugins = self.get_plugins()
        self.monitored_paths = self.get_monitored_paths()

    def parse(self):
        log.info('Parsing %s' % self.path)

        # Get the build files from the root of the source
        build_files = get_build_files(self.path)

        # Determine the node declaration from the root build files
        self.stretch_data = get_data(build_files['stretch'])
        nodes = self.stretch_data.get('nodes')

        if nodes:
            # Mulitple node declaration used
            self.multiple_nodes = True
            self.build_files = build_files

            for name, path in nodes.iteritems():
                node_path = os.path.join(self.path, path)
                self.nodes.append(Node(node_path, path, self, name))
        else:
            # Individual node declaration used
            self.multiple_nodes = False
            self.nodes.append(Node(self.path, self.relative_path, self))

    def get_plugins(self):
        log.info('Loading plugins...')

        plugins = []

        objects = self.nodes
        if self.multiple_nodes:
            objects = [self] + objects

        for obj in objects:
            obj_plugins = obj.stretch_data.get('plugins')
            if obj_plugins:
                for name, options in obj_plugins.iteritems():
                    plugins.append(create_plugin(name, options, obj))

        return plugins

    def get_monitored_paths(self):
        log.info('Searching for paths to monitor...')

        monitored_paths = {}

        def add_path(node, path):
            if node in monitored_paths:
                monitored_paths[node].append(path)
            else:
                monitored_paths[node] = [path]

        # Find app paths
        for node in self.nodes:
            if node.app_path:
                add_path(node, node.app_path)

        # Find plugin paths
        for plugin in self.plugins:
            add_path(plugin.parent, plugin.monitored_paths)

        return monitored_paths

    def build_and_push(self, release, system):
        [node.container.build(release, system, node) for node in self.nodes]

    def run_build_plugins(self, deploy, nodes=None):
        for plugin in self.plugins:
            if nodes and plugin.parent in nodes:
                plugin.build(deploy)

    def run_pre_deploy_plugins(self, deploy, nodes=None):
        for plugin in self.plugins:
            if nodes and plugin.parent in nodes:
                plugin.pre_deploy(deploy)

    def run_post_deploy_plugins(self, deploy, nodes=None):
        for plugin in self.plugins:
            if nodes and plugin.parent in nodes:
                plugin.post_deploy(deploy)

    def copy_to_buffer(self, path):
        dir_util.copy_tree(self.path, path)

    def get_app_paths(self):
        app_paths = {}
        for node in self.nodes:
            if node.app_path:
                app_paths[node.name] = node.app_path
        return app_paths

    @contextmanager
    def mount_templates(self, path):
        """
        path/
            node.name/
                template1
                template2
            node.name/
                template1
                template2
        """
        for node in self.nodes:
            dest_path = os.path.join(path, node.name)
            utils.clear_path(dest_path)
            templates_path = os.path.join(node.container.path, 'templates')
            if os.path.exists(templates_path):
                dir_util.copy_tree(templates_path, dest_path)
        yield
        utils.clear_path(path)


class Node(object):
    def __init__(self, path, relative_path, snapshot, name=None):
        self.path = os.path.realpath(path)
        self.relative_path = relative_path
        self.name = name
        self.snapshot = snapshot

        # Begin parsing node
        self.parse()

    def parse(self):
        log.info('Parsing node %s' % self.relative_path)

        # Get the build files from the root of the node
        self.build_files = get_build_files(self.path)

        # Find node's name if not defined
        stretch_file = self.build_files['stretch']
        self.stretch_data = get_data(stretch_file)
        if not self.name:
            self.name = self.stretch_data.get('name')
            if not self.name:
                raise exceptions.UndefinedParam('name', stretch_file)

        # Find containers
        container = self.stretch_data.get('container')
        if container:
            path = os.path.join(self.path, container)
        else:
            path = self.path
        self.container = Container.create(path, self.snapshot.containers,
                                          ancestor_paths=[])

        # Find app path
        self.app_path = os.path.join(self.container.path, 'app')
        if not os.path.exists(self.app_path):
            self.app_path = None


class Container(object):
    def __init__(self, path, containers, parent, ancestor_paths):
        self.base_container = None
        self.path = path
        self.parent = parent
        self.built = False

        # Check for reference loop
        if self.path in ancestor_paths:
            raise Exception('Encountered container reference loop.')
        ancestor_paths.append(self.path)

        def expect(path):
            if not os.path.exists(path):
                raise exceptions.MissingFile(path)

        # Find Dockerfile
        self.dockerfile_path = os.path.join(self.path, 'Dockerfile')
        if not os.path.exists(self.dockerfile_path):
            raise exceptions.MissingFile(self.dockerfile_path)

        # Make required directories and files
        utils.makedirs(os.path.join(self.path, 'files'))
        utils.makedirs(os.path.join(self.path, 'app'))
        if not os.path.exists(os.path.join(self.path, 'files/autoload.sh')):
            with open(os.path.join(self.path, 'files/autoload.sh'), 'w') as f:
                f.write('exit 3')

        # Parse and find base containers
        container_path = os.path.join(self.path, 'container.yml')
        if os.path.exists(container_path):
            container_data = get_data(container_path)

            base_path = container_data.get('from')
            if base_path:
                base_container_path = os.path.join(self.path, base_path)
                self.base_container = Container.create(
                    base_container_path, containers, self, ancestor_paths)

    @classmethod
    def create(cls, path, containers, parent=None, ancestor_paths=[]):
        path = os.path.realpath(path)

        for container in containers:
            if container.path == path:
                return container

        return cls(path, containers, parent, ancestor_paths)

    def build(self, release, system, node):
        if not self.built:
            # Recursively build and push base containers
            if self.base_container:
                self.base_container.build(release, system, node)

            # Generate Dockerfile
            dockerdata = read_file(self.dockerfile_path)

            """ TODO: Use when docker build gets ADD caching
            added_paths = (
                'ADD files /usr/share/stretch/files\n'
                'ADD app /usr/share/stretch/app\n'
                'ADD autoload.sh /usr/share/stretch/autoload.sh\n'
            )

            if self.base_container:
                # Add paths at beginning
                dockerdata = (('FROM %s\n' % self.base_container.tag) +
                             added_paths + dockerdata)"""
            added_paths = ''

            if self.base_container:
                # Add paths at beginning
                dockerdata = 'FROM %s\n' % self.base_container.tag + dockerdata
            else:
                # Add paths after FROM declaration
                lines = []
                from_found = False

                for line in dockerdata.split('\n'):
                    lines.append(line)
                    if (not from_found and
                            line.strip().lower().startswith('from')):
                        lines.append(added_paths)
                        from_found = True

                if not from_found:
                    raise Exception('no origin image defined')

                dockerdata = '\n'.join(lines)

            # Remove EXPOSE declarations since ports are handled by stretch
            dockerdata = '\n'.join([l for l in dockerdata.split('\n')
                          if not l.strip().lower().startswith('expose')])

            # Generate tag
            if self.parent:
                # Base container
                self.tag = 'stretch_base/sys%s' % system.pk
            elif release:
                # Node container
                self.tag = node.get_image()
            else:
                # Local container
                self.tag = node.get_image(local=True)

            # Build image
            log.info('Building %s' % self.tag)
            with open(os.path.join(self.path, 'Dockerfile'), 'w') as f:
                f.write(dockerdata)

            log.debug(docker_client.build(self.path, self.tag))

            # Push node containers to registry
            if not self.parent:
                log.info('Pushing %s to registry' % self.tag)
                # TODO: use api for push
                log.debug(utils.check_output(['docker', 'push', self.tag]))
                # log.debug(docker_client.push(self.tag))
                # TODO: .dockercfg in docs, docker login

            # TODO: clean up base images
            self.built = True


def read_file(path):
    with open(path) as source:
        return source.read()


def get_data(path):
    return yaml.load(read_file(path)) or {}


def get_build_files(path):
    """
    Return all build files in a path.
    """
    build_files = {}

    stretch_path = os.path.join(path, 'stretch.yml')
    if os.path.exists(stretch_path):
        build_files['stretch'] = stretch_path
    else:
        raise exceptions.MissingFile(stretch_path)

    return build_files
