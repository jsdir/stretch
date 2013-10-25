import etcd
import collections

from stretch import utils


class ConfigManager(object):

    def add_env(self, env):
        self.sync_env_name(env)
        self.sync_env_config(env)

    def remove_env(self, env):
        self.delete(self.get_key(env))

    def sync_env_name(self, env):
        """
        Called after an environment is created or after its name is changed.
        """
        self.set('%s/name' % self.get_key(env), env.name)

    def sync_env_config(self, env):
        """
        Called after an environment is created or after its config is changed.
        """
        self.set_dict('%s/config' % self.get_key(env), env.config)

    def add_group(self, group):
        [self.add_instance(instance, group) for instance in group.instances]

    def remove_group(self, group):
        # TODO: sync group name changes
        self.delete('%s/groups/%s' % (self.get_key(env), group.name))

    def add_host(self, host):
        [self.add_instance(instance) for instance in host.instances]

    def remove_host(self, host):
        # TODO: sync host name changes
        self.delete('%s/hosts/%s' % (self.get_key(env), host.name))

    def add_instance(self, instance):
        # host's parent can be either an environment or a group
        host = instance.host
        env = host.environment
        if host.group:
            parent_key = 'groups'
            parent_id = str(host.group.pk)
        else:
            parent_key = 'hosts'
            parent_id = str(host.pk)

        key = '%s/%s/%s' % (self.get_key(env), parent_key, parent_id)

        instance.node.ports
        ports = []
        instance_data = {
            'address': host.address,
            'ports': {

            }
        }

        self.set_dict('%s/%s' % (key, str(instance.pk)), instance_data)

    def remove_instance(self, instance):
        self.delete('%s/hosts/%s' % (self.get_key(env), host.name))

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
