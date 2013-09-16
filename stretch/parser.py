import os
import sys
import yaml
import collections
import gnupg
from distutils import dir_util

from stretch import utils


class SourceParser(object):
    def __init__(self, path):
        self.path = path

        # Initial parse
        self.parse()

        # Automatically decrypt
        self.decrypt_secrets()

    def parse(self):
        self.files = self.parse_node(self.path)

        root = self.get_data(self.files['stretch'])
        nodes = root.get('nodes')

        if nodes:
            # Mulitple node declaration used
            self.multiple_nodes = True
            self.files['nodes'] = {}

            for node_name, node_path in nodes.iteritems():
                self.files['nodes'][node_name] = self.parse_node(node_path)
        else:
            # Individual node declaration used
            self.multiple_nodes = False

    def parse_node(self, path):
        build_files = {}

        stretch_path = os.path.join(path, 'stretch.yml')
        if os.path.exists(stretch_path):
            build_files['stretch'] = stretch_path
        else:
            raise Exception('No stretch.yml defined in root node directory')

        config_path = os.path.join(path, 'config.yml')
        if config_path:
            build_files['config'] = config_path

        secrets_path = os.path.join(path, 'secrets.yml')
        if secrets_path:
            build_files['secrets'] = secrets_path

        return build_files

    def decrypt_secrets(self):
        gpg = gnupg.GPG()

        root_secrets = self.files.get('secrets')
        if root_secrets:
            self.decrypt_file(root_secrets, gpg)

        if self.multiple_nodes:
            for node_name, node in self.files['nodes'].iteritems():
                node_secrets = node.get('secrets')
                if node_secrets:
                    self.decrypt_file(node_secrets, gpg)

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
                raise TypeError('Expected String, Array, or Hash, got %s'
                                % type(element))

        def decrypt_text(data):
            return gpg.decrypt(data)

        decrypted_data = decrypt_element(self.get_data(path))
        with open(path, 'w') as source:
            yaml.dump(decrypted_data, source)

    def get_data(self, path):
        data = None
        if os.path.exists(path):
            with open(path) as source:
                data = yaml.load(source.read())
        return data

    def read_file(self, path):
        with open(path) as source:
            return source.read()

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
        root_config = self.files.get('config')

        if self.multiple_nodes:
            if root_config:
                config['global'] = self.read_file(root_config)

            config['nodes'] = {}
            for node_name, node in self.files['nodes'].iteritems():
                node_config = node.get('config')
                if node_config:
                    config['nodes'][node_name] = self.read_file(node_config)

        else:
            name = self.get_individual_node_name()
            if root_config:
                config[name] = self.read_file(root_config)

        return config

    def copy_to_buffer(self, path):
        if self.multiple_nodes:
            dir_util.copy_tree(self.path, path)
        else:
            node_name = self.get_individual_node_name()
            node_path = os.path.join(path, node_name)
            utils.makedirs(node_path)
            dir_util.copy_tree(self.path, node_path)

    def get_individual_node_name(self):
        root = self.get_data(self.files['stretch'])
        name = root.get('name')
        if not name:
            raise Exception('No name defined for node.')
        return name


def get_nodes(path):
    result = {'plugins': {}, 'nodes': {}}

    data = get_node(path)
    if data:
        nodes = data.get('nodes')
        if nodes:
            # file is root descriptor

            # global configuration
            config = data.get('config') or {}

            # local options
            local_options = {}
            local_data = data.get('local_options')
            if local_data:
                for options in local_data.values():
                    if options.has_key('includes'):
                        includes = options.pop('includes')
                        for node_name in includes:
                            if local_options.has_key(node_name):
                                update(local_options[node_name], options)
                            else:
                                local_options[node_name] = options

            # plugins
            plugins = data.get('plugins')
            if plugins:
                result['plugins'] = plugins

            for node_name, node_path in nodes.iteritems():
                full_node_path = os.path.join(path, node_path)

                # apply global configuration
                node_data = {'config': dict(config)}

                # apply local options
                node_local_data = local_options.get(node_name)
                if node_local_data:
                    update(node_data, node_local_data)

                # apply file options
                update(node_data, get_node(full_node_path))

                result['nodes'][node_name] = node_data
        else:
            # file is node descriptor
            node_data = get_node(path)
            node_name = node_data.get('node')
            if node_name:
                result['nodes'][node_name] = node_data
            else:
                # no node name error
                pass

    return result


def get_node(path):
    stretch_file = os.path.join(path, 'stretch.yml')
    data = {}

    if os.path.exists(stretch_file):
        with open(stretch_file) as source:
            data = yaml.load(source.read())

    return data


def parse(path):
    stretch_file = os.path.join(path, 'stretch.yml')
    data = {}

    if os.path.exists(stretch_file):
        with open(stretch_file) as source:
            data = yaml.load(source.read())

    return data


def decrypt_secrets(path):
    gpg = gnupg.GPG()

    data = get_data(os.path.join(path, 'stretch.yml'))
    nodes = data.get('nodes')

    secret_files = []

    def get_secret_file(path):
        secrets_file = os.path.join(path, 'secrets.yml')

        result = []
        if os.file.exists(secrets_file):
            result.append(secrets_file)

        return result

    secret_files += get_secret_file(path)

    if nodes:
        for node_name, node_path in nodes.iteritems():
            secret_files += get_secret_file(os.path.join(path, node_path))

    [decrypt_file(secret_file, gpg) for secret_file in secret_files]


def decrypt_file(path, gpg):

    def decrypt_element(element):
        if isinstance(element, str):
            return decrypt_text(element)
        elif isinstance(element, list):
            return map(decrypt_element, element)
        elif isinstance(element, dict):
            return dict(zip(element.keys(),
                            map(decrypt_element, element.values())))
        else:
            raise TypeError('Expected String, Array, or Hash, got %s'
                            % type(element))

    def decrypt_text(data):
        return gpg.decrypt(data)

    decrypted_data = decrypt_element(get_data(path))
    with open(path, 'w') as source:
        yaml.dump(decrypted_data, source)
