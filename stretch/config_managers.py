import etcd
import collections

from stretch import utils


class ConfigManager(object):

    def add_env(self, env):
        self.set('%s/name' % self.get_key(env), env.name)
        self.sync_env_config(env)

    def sync_env_config(self, env):
        self.set_dict('%s/config' % self.get_key(env), env.config)

    def remove_env(self, env):
        self.delete(self.get_key(env))

    def add_instance(self, instance):
        self.set_dict(self.get_instance_key(instance), {
            'address': instance.host.address,
            'ports': {},
            'enabled': False
        })

    def remove_instance(self, instance):
        self.delete(self.get_instance_key(instance))

    def get_instance_key(self, instance):
        host = instance.host
        if host.group:
            parent_key = 'groups'
            parent_id = str(host.group.pk)
        else:
            parent_key = 'hosts'
            parent_id = str(host.pk)

        return '/'.join([self.get_key(host.environment), parent_key, parent_id,
                         str(instance.pk)])

    def get_key(self, env):
        return '/%s/envs/%s' % (env.system.pk, env.pk)

    def set_dict(self, root_key, dict_value):
        for key, value in dict_value.iteritems():
            value_key = '%s/%s' % (root_key, key)
            if isinstance(value, collections.Mapping):
                self.set_dict(value_key, value)
            else:
                self.set(value_key, value)

    def set(self, key, value):
        raise NotImplementedError

    def get(self, key):
        raise NotImplementedError

    def delete(self, key):
        raise NotImplementedError


class EtcdConfigManager(object):
    def __init__(self, address):
        try:
            host, port = address.split(':')
        except ValueError:
            raise ValueError('incorrectly formatted address "%s"; expected '
                             '"ip:port"' % address)
        self.etcd_client = etcd.Client(host=host, port=int(port))

    def set(self, key, value):
        self.etcd_client.set(key, value)

    def get(self, key):
        return self.etcd_client.get(key).value

    def delete(self, key):
        self.etcd_client.delete(key)


@utils.memoized
def get_config_manager():
    return EtcdConfigManager('localhost:4001')
