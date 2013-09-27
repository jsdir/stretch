import os
import sys
import yaml
import collections
import gnupg
import docker
import logging
from distutils import dir_util

from stretch import utils, contexts
from stretch.plugins import create_plugin


log = logging.getLogger('stretch')
docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.4')


class Container(object):
    def __init__(self, path, parent=None, ancestor_paths=[]):
        self.from_container = None
        self.path = os.path.realpath(path)
        self.parent = parent

        # Check for reference loop
        if self.path in ancestor_paths:
            raise Exception('Encountered container reference loop.')
        ancestor_paths.append(self.path)

        # Parse and find base containers
        container_path = os.path.join(self.path, 'container.yml')
        if os.path.exists(container_path):
            container_data = get_data(container_path)

            from_path = container_data.get('from')
            if from_path:
                from_container_path = os.path.join(self.path, from_path)
                self.from_container = Container(from_container_path, self,
                                                ancestor_paths)


class Node(object):
    def __init__(self, path, relative_path, name=None):
        self.path = os.path.realpath(path)
        self.relative_path = relative_path
        self.name = name

        # Begin parsing node
        self.parse()

    def parse(self):
        log.info('Parsing node %s' % self.relative_path)

        # Get the build files from the root of the node
        self.build_files = get_build_files(self.path)

        # Find node's name if not defined
        self.stretch_data = get_data(self.build_files['stretch'])
        if not self.name:
            self.name = self.stretch_data.get('name')
            if not self.name:
                raise Exception('No name defined for node.')

        # Find containers
        container = self.stretch_data.get('container')
        if container_path:
            self.container = Container(os.path.join(self.path, container))
        else:
            self.container = Container(self.path)

        # Find app path
        app_path = os.path.join(self.container.path, 'app')
        if not os.path.exists(app_path):
            app_path = None

    def build_and_push(self, release):
        system, sha = release.system, release.sha
        # Build and plush series of containers
        #tag = self.build_container(self.container_path, self.name, system, sha)
        #docker_client.push(tag)

    def build_container(self, path, image_name, system, sha):
        # Build dependencies
        container_data = None
        container_path = os.path.join(path, 'container.yml')
        if os.path.exists(container_path):
            container_data = get_data(container_path)
            base_path = container_data.get('from')

            if base_path:
                if path == base_path:
                    raise Exception('Encountered container reference loop.')

                self.build_container(base_path, None, system.name, sha)

        if image_name:
            tag = '%s/%s' % (system.name, image_name)
            tag = '%s:%s' % (tag, sha)
        else:
            if not container_data:
                raise Exception('No container.yml for dependency.')
            name = container_data.get('name')
            if not name:
                raise Exception('No name defined for container.')
            tag = '%s/%s' % (system.name, name)

        docker_client.build(path, tag)
        return tag


class SourceParser(object):
    def __init__(self, path):
        self.path = path
        self.relative_path = '/'
        self.nodes = []
        self.release = None

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
                self.nodes.append(Node(node_path, path, name))
        else:
            # Individual node declaration used
            self.multiple_nodes = False
            self.nodes.append(Node(self.path, '/'))

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
            if monitored_paths.has_key(node):
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

    def build_and_push(self, system, sha):
        [node.build_and_push(system, sha) for node in self.nodes]

    def run_build_plugins(self, environment, nodes=None):
        for plugin in self.plugins:
            if nodes != None or plugin.parent in nodes:
                plugin.build(environment)

    def run_pre_deploy_plugins(self, environment, existing_parser,
                               nodes=None):
        for plugin in self.plugins:
            if nodes != None or plugin.parent in nodes:
                plugin.pre_deploy(environment, self, existing_parser)

    def run_post_deploy_plugins(self, environment, existing_parser,
                                nodes=None):
        for plugin in self.plugins:
            if nodes != None or plugin.parent in nodes:
                plugin.post_deploy(environment, self, existing_parser)

    def copy_to_buffer(self, path):
        dir_util.copy_tree(self.path, path)

    def get_release_config(self):
        """
        Return configuration that can be easily reconstructed

        If individual:
            Returns: {
                nodes: {
                    node_name: config_source,
                }
            }
        If multiple:
            Returns: {
                global: config_source,
                nodes: {
                    node_name: config_source,
                    node_name: config_source
                }
            }
        """
        config = {}

        if self.multiple_nodes:
            config['global'] = {'config': ''}
            config_file = self.build_files.get('config')
            if config_file:
                config['global']['config'] = read_file(config_file)

        for node in self.nodes:
            config['nodes'][node.name] = {'config': ''}
            config_file = node.build_files.get('config')
            if config_file:
                config['nodes'][node.name]['config'] = read_file(config_file)

        return config

    def mount_templates(self, path):
        """
        path/
            node_name/
                template1
                template2
            node_name/
                template1
                template2
        """
        """
        for node in self.nodes:
            dest_path = os.path.join(path, node.name)
            utils.clear_path(dest_path)
            templates_path = os.path.join(node.container_path, 'templates')
            if os.path.exists(templates_path):
                dir_util.copy_tree(templates_path, dest_path)
        """
        pass


def read_file(path):
    with open(path) as source:
        return source.read()


def get_data(path):
    return yaml.load(read_file(path))


def get_build_files(path):
    """
    Return all build files in a path.
    """
    build_files = {}

    stretch_path = os.path.join(path, 'stretch.yml')
    if os.path.exists(stretch_path):
        build_files['stretch'] = stretch_path
    else:
        raise Exception('No stretch.yml exists in node path.')

    config_path = os.path.join(path, 'config.yml')
    if os.path.exists(config_path):
        build_files['config'] = config_path

    return build_files
