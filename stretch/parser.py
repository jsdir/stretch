import os
import sys
import yaml
import collections
import gnupg
import docker
from distutils import dir_util

from stretch import utils


docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.4')


class Node(object):
    def __init__(self, path, name=None):
        self.name = name
        self.path = path

        # Load from path
        build_files = parse_node(self.path)
        self.stretch = build_files.get('stretch')
        self.secrets = build_files.get('secrets')
        self.config = build_files.get('config')

        data = get_data(self.stretch)

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
    def __init__(self, path):
        self.path = path
        self.nodes = []
        self.parse()

    def parse(self):
        root_files = parse_node(self.path)
        root = self.get_data(root_files['stretch'])
        nodes = root.get('nodes')

        if nodes:
            # Mulitple node declaration used
            self.multiple_nodes = True
            self.global_files = root_files

            for name, path in nodes.iteritems():
                self.nodes.append(Node(path, name))
        else:
            # Individual node declaration used
            self.multiple_nodes = False
            self.nodes.append(Node(self.path))

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


def get_data(path):
    data = None
    if os.path.exists(path):
        data = yaml.load(read_file(path))
    return data
