import yaml

from stretch import exceptions, utils

config = {'config': None}
defaults = {
    # Directories
    'data_dir': '/var/lib/stretch',
    'cache_dir': '/var/cache/stretch',
    'temp_dir': '/tmp/stretch',

    # Services
    'etcd': 'localhost:4001',
    'etcd_namespace': 'stretch',
    'registry': 'localhost:5000',
    'registry_namespace': 'stretch',

    # Containers
    'router_container': '',
    'agent_container': ''
}
required_keys = [
    'database_path',
    #'database_username',
    #'database_password'
]


class ConfigException(Exception): pass


def set_config_file(config_file):
    config['config'] = defaults
    utils.merge(config['config'], yaml.load(open(config_file, 'r')))
    for key in required_keys:
        if key not in config['config']:
            raise ConfigException('key "%s" is required in config.yml' % key)


def get_config():
    if not config['config']:
        raise ConfigException('No configuration defined. Either set '
            'STRETCH_CONFIG or use the --config flag to point to a valid '
            'configuration file.')
    return config['config']
