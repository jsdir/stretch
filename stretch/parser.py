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


class SourceParser(object):
    def __init__(self, path):
        self.path = path
        self.relative_path = '/'
        self.nodes = []

        # Begin parsing source
        self.parse()

        log.info('Loading plugins...')
        self.plugins = self.get_plugins()
        self.load_plugins()
        self.load_monitored_paths()

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

        # Find app paths
        for node in self.nodes:
            app_path = os.path.join(node.container.path, 'app')
            if os.path.exists(app_path):
                if monitored_path.has_key(node):
                    monitored_paths[node].append(app_path)
                else:
                    monitored_paths[node] = [app_path]

        # Find plugin paths
        for plugin in self.plugins:
            monitored_paths += plugin.monitored_paths

        return monitored_paths

    def run_build_plugins(self):
        [plugin.build() for plugin in self.plugins]

    def run_pre_deploy_plugins(self, existing, environment):
        for plugins in self.plugins:
            plugin.pre_deploy(self, existing, environment)

    def run_post_deploy_plugins(self, existing, environment):
        for plugins in self.plugins:
            plugin.post_deploy(self, existing, environment)


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

class SourceParser(object):
    def __init__(self, path, release=None, decrypt_secrets=False):
        self.path = path
        self.release = release
        self.nodes = []
        self.parse()

        if decrypt_secrets:
            self.decrypt_secrets()

        self.finalize_nodes()
        self.load_secrets()
        self.load_plugins()

    def parse(self):
        root_files = parse_node(self.path)
        root = self.get_data(root_files['stretch'])
        nodes = root.get('nodes')

        if nodes:
            # Mulitple node declaration used
            self.multiple_nodes = True
            self.global_files = root_files

            for name, path in nodes.iteritems():
                node_path = os.path.join(self.path, path)
                self.nodes.append(Node(node_path, path, name))
        else:
            # Individual node declaration used
            self.multiple_nodes = False
            self.nodes.append(Node(self.path, '/'))

    def finalize_nodes(self):
        [node.finalize() for node in self.nodes]

    def load_secrets(self):
        if self.multiple_nodes:
            self.secret_data = get_data(self.global_files.get('secrets')) or {}

    def load_plugins(self):
        self.plugins = []
        local_stretch = None

        if self.multiple_nodes:
            data = get_data(self.global_files.get('stretch'), self.secret_data)

            global_plugins = data.get('plugins')

            if global_plugins:
                for name, options in global_plugins.iteritems():
                    self.plugins.append(create_plugin(name, options,
                                                      self.path, '/'))

            local_stretch = data.get('local_stretch')

        for node in self.nodes:
            node_plugins = {}

            if local_stretch:
                for conf in local_stretch.values():
                    local_plugins = conf.get('plugins')
                    includes = conf.get('includes')
                    if includes and local_plugins and node.name in includes:
                        utils.update(node_plugins, local_plugins)

            if node.plugins:
                update(node_plugins, node.plugins)

            for name, options in node_plugins.iteritems():
                self.plugins.append(create_plugin(name, options, node.path,
                                                  node.relative_path))

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
        for node in self.nodes:
            dest_path = os.path.join(path, node.name)
            utils.clear_path(dest_path)
            templates_path = os.path.join(node.container_path, 'templates')
            if os.path.exists(templates_path):
                dir_util.copy_tree(templates_path, dest_path)

    def decrypt_secrets(self):
        gpg = gnupg.GPG()

        # Decrypt global secrets
        if self.multiple_nodes:
            global_secrets = self.global_files.get('secrets')
            if global_secrets:
                self.decrypt_file(global_secrets, gpg)

        # Decrypt node secrets
        for node in self.nodes:
            if node.secrets:
                self.decrypt_file(node.secrets, gpg)

    def decrypt_file(self, path, gpg):

        def decrypt_element(element):
            if isinstance(element, str):
                return decrypt_text(element)
            elif isinstance(element, list):
                return map(decrypt_element, element)
            elif isinstance(element, dict):
                return dict(zip(element.keys(),
                                map(decrypt_element, element.values())))
            else:
                raise TypeError('Expected String, Array, or Hash, got %s.'
                                % type(element))

        def decrypt_text(data):
            return gpg.decrypt(data)

        decrypted_data = decrypt_element(get_data(path))
        with open(path, 'w') as source:
            yaml.dump(decrypted_data, source)

    def get_release_config(self):
        """
        If individual:
            Returns: {
                nodes: {
                    node_name: {
                        config: config_source,
                        secrets: secrets
                    }
                }
            }
        If multiple:
            Returns: {
                global: {
                    config: config_source,
                    secrets: secrets
                },
                nodes: {
                    node_name: {
                        config: config_source,
                        secrets: secrets
                    },
                    node_name: {
                        config: config_source,
                        secrets: secrets
                    }
                }
            }
        """
        config = {}

        if self.multiple_nodes:
            config['global'] = {
                'config': '',
                'secrets': self.secret_data
            }
            root_config = self.global_files.get('config')
            if root_config:
                config['global']['config'] = read_file(root_config)

        for node in self.nodes:
            config['nodes'][node.name] = {
                'config': '',
                'secrets': node.secret_data
            }
            if node.config:
                config['nodes'][node.name]['config'] = read_file(node.config)

        return config

    def copy_to_buffer(self, path):
        if self.multiple_nodes:
            dir_util.copy_tree(self.path, path)
        else:
            node_name = self.nodes[0].name
            node_path = os.path.join(path, node_name)
            utils.makedirs(node_path)
            dir_util.copy_tree(self.path, node_path)

    def build_and_push(self, sha):
        [node.build_and_push(sha) for node in self.nodes]

    def run_build_plugins(self):
        [plugin.build() for plugin in self.plugins]

    def run_pre_deploy_plugins(self, existing, environment):
        for plugins in self.plugins:
            plugin.pre_deploy(self, existing, environment)

    def run_post_deploy_plugins(self, existing, environment):
        for plugins in self.plugins:
            plugin.post_deploy(self, existing, environment)


def parse_node(path):
    build_files = {}

    stretch_path = os.path.join(path, 'stretch.yml')
    if os.path.exists(stretch_path):
        build_files['stretch'] = stretch_path
    else:
        raise Exception('No stretch.yml defined in root node directory.')

    config_path = os.path.join(path, 'config.yml')
    if os.path.exists(config_path):
        build_files['config'] = config_path

    secrets_path = os.path.join(path, 'secrets.yml')
    if os.path.exists(secrets_path):
        build_files['secrets'] = secrets_path

    return build_files


def read_file(path):
    with open(path) as source:
        return source.read()


def get_dotted_key_value(key, data):
    try:
        keys = key.split('.')
        data_key = keys.pop(0)

        if isinstance(data, dict):
            new_data = data[data_key]
        else:
            raise KeyError

        if keys:
            return get_dotted_key_value('.'.join(keys), new_data)
        else:
            return new_data

    except KeyError:
        # TODO: logger
        print 'Key not found in data.'
        return None


def load_yaml_data(data, secrets=None):

    def null_constructor(loader, node):
        return None

    def secret_constructor(secrets):

        def constructor(loader, node):
            key = loader.construct_scalar(node)
            result = get_dotted_key_value(key, secrets) or 'None'
            return result

        return constructor

    if secrets:
        constructor = secret_constructor(secrets)
    else:
        constructor = null_constructor
    yaml.add_constructor('!secret', constructor)

    return yaml.load(data)


def get_data(path, secrets=None):
    data = None
    if os.path.exists(path):
        data = load_yaml_data(read_file(path))
    return data


def parse_release_config(config, new_release, existing_release, environment):
    # TODO: use in SourceParser.load_plugins, refactor

    def get_config(data):
        secrets = data.get('secrets')
        contexts = [contexts.create_deploy_context(new_release,
            existing_release, environment)]
        config = utils.render_template(data.get('config'), contexts)
        return load_yaml_data(config, secrets)

    result = {}
    global_data = config.get('global')

    if global_data:
        config_file = get_config(global_data)
        global_config = config_file.get('config') or {}

        for block in (config_file.get('local_config') or {}).iteritems():
            for include in (block.get('includes') or []):
                node_config = {}
                utils.update(node_config, global_config)
                utils.update(node_config, (block.get('config') or {})))
                result[include] = node_config

    for name, data in config.get('nodes').iteritems():
        node_config = {}
        update(node_config, global_config)
        update(node_config, (get_config(data) or {}))

        if result.has_key(name):
            update(result[name], node_config)
        else:
            result[name] = node_config

    return result
