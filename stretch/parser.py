import os
import sys
import yaml
import collections
import gnupg
import docker
import logging
from distutils import dir_util
from django.conf import settings
from StringIO import StringIO

from stretch import utils, contexts
from stretch.plugins import create_plugin


log = logging.getLogger('stretch')
docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.4')


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

        # Find Dockerfile
        self.dockerfile_path = os.path.join(self.path, 'Dockerfile')
        if not os.path.exists(self.dockerfile_path):
            raise Exception('Dockerfile not found.')

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

    def build(self, release, node):
        if not self.built:
            # Recursively build and push base containers
            if self.base_container:
                self.base_container.build(release, node)

            # Generate Dockerfile
            dockerdata = read_file(self.dockerfile_path)

            added_paths = (
                'ADD files /usr/share/stretch/files\n'
                'ADD app /usr/share/stretch/app\n'
            )

            if self.base_container:
                # Add paths at beginning
                dockerdata = (('FROM %s\n' % self.base_container.tag) +
                             added_paths + dockerdata)
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
                    raise Exception('No origin image defined.')

                dockerdata = '\n'.join(lines)

            # Remove EXPOSE declarations since ports are handled by stretch
            dockerdata = '\n'.join([l for l in dockerdata.split('\n')
                          if not l.strip().lower().startswith('expose')])

            # Create and use generated Dockerfile
            dockerfile = StringIO(dockerdata)

            # Generate tag
            if self.parent:
                # Base container
                self.tag = 'stretch_base/%s' % utils.generate_random_hex(16)
            elif release:
                # Node container
                self.tag = '%s/%s#%s' % (settings.REGISTRY_URL, node.name,
                    release.sha)
            else:
                # Local container
                self.tag = 'stretch/%s' % node.name

            # Build image
            log.info('Building %s' % self.tag)
            docker_client.build(self.path, self.tag, fileobj=dockerfile)

            # Push node containers to registry
            if not self.parent:
                pass #docker_client.push(self.tag)

            # TODO: clean up base images
            self.built = True


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
        self.stretch_data = get_data(self.build_files['stretch'])
        if not self.name:
            self.name = self.stretch_data.get('name')
            if not self.name:
                raise Exception('No name defined for node.')

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


class Snapshot(object):
    def __init__(self, path, release=None):
        self.path = path
        self.relative_path = '/'
        self.nodes = []
        self.release = release
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
            self.nodes.append(Node(self.path, '/', self))

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

    def build_and_push(self, release):
        [node.container.build(release, node) for node in self.nodes]

    def build_local(self):
        [node.container.build(None, node) for node in self.nodes]

    def run_build_plugins(self, deploy, nodes=None):
        for plugin in self.plugins:
            if nodes != None or plugin.parent in nodes:
                plugin.build(deploy)

    def run_pre_deploy_plugins(self, deploy, nodes=None):
        for plugin in self.plugins:
            if nodes != None or plugin.parent in nodes:
                plugin.pre_deploy(deploy)

    def run_post_deploy_plugins(self, deploy, nodes=None):
        for plugin in self.plugins:
            if nodes != None or plugin.parent in nodes:
                plugin.post_deploy(deploy)

    def copy_to_buffer(self, path):
        dir_util.copy_tree(self.path, path)

    def get_config(self):
        """
        Return configuration that can be easily reconstructed

        If individual:
            Returns: {
                nodes: {
                    node.pk: config_source,
                }
            }
        If multiple:
            Returns: {
                global: config_source,
                nodes: {
                    node.pk: config_source,
                    node.pk: config_source
                }
            }
        """
        config = {'nodes': {}}

        if self.multiple_nodes:
            config_file = self.build_files.get('config')
            if config_file:
                config['global'] = read_file(config_file)

        for node in self.nodes:
            config_file = node.build_files.get('config')
            if config_file:
                config['nodes'][node.name] = read_file(config_file)

        return config

    def mount_templates(self, path):
        """
        path/
            node.pk/
                template1
                template2
            node.pk/
                template1
                template2
        """
        for node in self.nodes:
            dest_path = os.path.join(path, str(node.pk))
            utils.clear_path(dest_path)
            templates_path = os.path.join(node.container.path, 'templates')
            if os.path.exists(templates_path):
                dir_util.copy_tree(templates_path, dest_path)


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
        raise Exception('No stretch.yml exists in node path.')

    config_path = os.path.join(path, 'config.yml')
    if os.path.exists(config_path):
        build_files['config'] = config_path

    return build_files

def parse_release_config(config, environment, new_release, existing_release):

    def get_config(data):
        contexts = [contexts.create_deploy_context(environment, new_release,
                                                   existing_release)]
        config = utils.render_template(data, contexts)
        return yaml.load(config)

    result = {}
    global_config = {}
    nodes_config = {}
    global_data = config.get('global')

    if global_data:
        # Apply global configuration
        for block in get_config(global_data).iteritems():
            block_config = block.get('config', {})
            block_nodes = block.get('nodes', [])

            if block_nodes:
                # Local block
                for node in block_nodes:
                    if nodes_config.has_key(node):
                        utils.update(nodes_config[node], block_config)
                    else:
                        nodes_config[node] = block_config
            else:
                # Global block
                utils.update(global_config, block_config)

    # Apply node configuration
    for name, data in nodes_config.iteritems():
        node_config = {}
        utils.update(node_config, global_config)
        utils.update(node_config, data)
        result[name] = node_config

    for name, data in config.get('nodes').iteritems():
        node_config = {}
        utils.update(node_config, global_config)
        utils.update(node_config, nodes_config.get(name, {}))
        utils.update(node_config, (get_config(data) or {}))

        if result.has_key(name):
            utils.update(result[name], node_config)
        else:
            result[name] = node_config

    return result
