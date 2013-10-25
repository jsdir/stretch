from mock import Mock, patch
from nose.tools import eq_, assert_raises
from testtools import TestCase

from stretch import config_managers, testutils


class TestConfigManager(object):
    def setUp(self):
        self.cm = config_managers.ConfigManager()

    """
    def test_add_instance(self):
        instance = Mock()
        with patch.object(self.cm.set, Mock()) as func:
            self.cm.add_instance(instance)
            instance_data = {'fqdn': 'a.a.com'}
            func.assert_called_with('/sys_id/env_id/group_name/instance_id', instance_data)

    def test_remove_instance(self, env_id, instance_id):
        with patch.object(self.cm.set, Mock()) as func:
            self.cm.create_host('fqdn', 'env_name')
            func.assert_called_with('/environments/env_name/')

    def test_set_config(self):
        env = Mock()
        self.cm.set_config(config, env)
    """


class TestEtcdConfigManager(TestCase):
    def setUp(self):
        super(TestEtcdConfigManager, self).setUp()

        p = patch('stretch.config_managers.EtcdConfigManager.etcd_client')
        self.addCleanup(p.stop)
        self.etcd_client = p.start()

        self.cm = config_managers.EtcdConfigManager()

    """
    def test_set(self):
        self.cm.set('/key', 'value')
        self.etcd_client.set.assert_called_with('/key', 'value')

    def test_get(self):
        self.etcd_client.get.return_value = testutils.mock_attr(value='value')
        eq_(self.cm.get('/key'), 'value')
        self.etcd_client.get.assert_called_with('/key')

        def mock_get(key):
            raise KeyError

        self.etcd_client.get = mock_get
        with assert_raises(KeyError):
            self.cm.get('/key')
    """
