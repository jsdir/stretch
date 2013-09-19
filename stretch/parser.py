import os
import sys
import yaml
import collections
import gnupg
import docker
from distutils import dir_util

from stretch import utils
from stretch.plugins import create_plugin


docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.4')


class Node(object):
    def __init__(self, path, relative_path, name=None):
        self.name = name
        self.path = path
        self.relative_path = relative_path

        # Load from path
        build_files = parse_node(self.path)
        self.stretch = build_files.get('stretch')
        self.secrets = build_files.get('secrets')
        self.config = build_files.get('config')

        secrets = get_data(self.secrets)
        data = get_data(self.stretch, secrets)

        if not self.name:
            # Get name for individual node
            self.name = data.get('name')
            if not self.name:
                raise Exception('No name defined for node.')

        self.container = data.get('container')
        self.plugins = data.get('plugins')

    def build_and_push(self, system, sha):
        path = self.path
        if self.container:
            path = os.path.join(path, self.container)
        tag = self.build_container(path, self.name, system, sha)
        docker_client.push(tag)

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
    def __init__(self, path, release=None):
        self.path = path
        self.release = release
        self.nodes = []
        self.parse()
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

    def load_plugins(self):
        self.plugins = []
        local_stretch = None

        if self.multiple_nodes:
            secrets = get_data(self.global_files.get('secrets'))
            data = get_data(self.global_files.get('stretch'), secrets)

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

    def get_combined_config(self):
        """
        If individual:
            Returns: {node_name: config_source}
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
            root_config = self.global_files.get('config')
            if root_config:
                config['global'] = read_file(root_config)

            config['nodes'] = {}
            for node in self.nodes:
                if node.config:
                    config['nodes'][node.name] = read_file(node.config)

        else:
            node = self.nodes[0]
            if node.config:
                config[node.name] = read_file(node.config)

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


def get_data(path, secrets=None):

    def null_constructor(loader, node):
        return None

    def secret_constructor(secrets):

        def constructor(loader, node):
            key = loader.construct_scalar(node)
            result = get_dotted_key_value(key, secrets) or 'None'
            return result

        return constructor

    data = None
    if os.path.exists(path):
        if secrets:
            constructor = secret_constructor(secrets)
        else:
            constructor = null_constructor
        yaml.add_constructor('!secret', constructor)
        data = yaml.load(read_file(path))
    return data
