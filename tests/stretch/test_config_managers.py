from mock import Mock, patch, DEFAULT, call
from nose.tools import eq_, assert_raises
from testtools import TestCase

from stretch import config_managers, testutils
from stretch.testutils import mock_attr


class TestConfigManager(object):
    def setUp(self):
        self.cm = config_managers.ConfigManager()

    @patch('stretch.config_managers.ConfigManager.get_key', return_value='/e')
    def test_add_env(self, get_key):
        env = mock_attr(name='env_name')
        with patch.multiple(self.cm, sync_env_config=DEFAULT,
                            set=DEFAULT) as values:
            self.cm.add_env(env)
            values['set'].assert_called_with('/e/name', 'env_name')
            values['sync_env_config'].assert_called_with(env)

    @patch.multiple('stretch.config_managers.ConfigManager', get_key=DEFAULT,
                    set_dict=DEFAULT)
    def test_sync_env_config(self, get_key, set_dict):
        get_key.return_value = '/e'
        env = mock_attr(config={'key': 'value'})
        self.cm.sync_env_config(env)
        set_dict.assert_called_with('/e/config', {'key': 'value'})

    @patch.multiple('stretch.config_managers.ConfigManager', get_key=DEFAULT)
    def test_remove_env(self, get_key):
        get_key.return_value = '/e'
        env = Mock()
        self.cm.delete = Mock()
        self.cm.remove_env(env)
        self.cm.delete.assert_called_with('/e')

    @patch.multiple('stretch.config_managers.ConfigManager', get_key=DEFAULT,
                    set_dict=DEFAULT)
    def test_add_instance_from_group(self, get_key, set_dict):
        get_key.return_value = '/e'
        host = mock_attr(group=mock_attr(pk=2), address='1.1.1.1',
                         environment=Mock())
        instance = mock_attr(host=host, pk=3)

        self.cm.add_instance(instance)

        set_dict.assert_called_with('/e/groups/2/3', {
            'address': '1.1.1.1',
            'ports': {},
            'enabled': False
        })

    @patch.multiple('stretch.config_managers.ConfigManager', get_key=DEFAULT,
                    set_dict=DEFAULT)
    def test_add_instance_from_hosts(self, get_key, set_dict):
        get_key.return_value = '/e'
        host = mock_attr(pk=2, address='1.1.1.1', environment=Mock(),
                         group=None)
        instance = mock_attr(host=host, pk=3)

        self.cm.add_instance(instance)

        set_dict.assert_called_with('/e/hosts/2/3', {
            'address': '1.1.1.1',
            'ports': {},
            'enabled': False
        })

    @patch.multiple('stretch.config_managers.ConfigManager', get_key=DEFAULT,
                    delete=DEFAULT)
    def test_remove_instance_from_groups(self, get_key, delete):
        get_key.return_value = '/e'
        host = mock_attr(pk=4, environment=Mock(), group=mock_attr(pk=2))
        instance = mock_attr(host=host, pk=3)
        self.cm.remove_instance(instance)
        delete.assert_called_with('/e/groups/2/3')

    @patch.multiple('stretch.config_managers.ConfigManager', get_key=DEFAULT,
                    delete=DEFAULT)
    def test_remove_instance_from_hosts(self, get_key, delete):
        get_key.return_value = '/e'
        host = mock_attr(pk=2, environment=Mock(), group=None)
        instance = mock_attr(host=host, pk=3)
        self.cm.remove_instance(instance)
        delete.assert_called_with('/e/hosts/2/3')

    def test_get_key(self):
        env = mock_attr(pk=2, system=mock_attr(pk=1))
        eq_(self.cm.get_key(env), '/1/envs/2')

    def test_set_dict(self):
        self.cm.set = Mock()
        self.cm.set_dict('/root', {'a': {'b': {}, 'c': None}, 'd': 2})
        self.cm.set.assert_has_calls([call('/root/a/c', None),
                                      call('/root/d', 2)])


class TestEtcdConfigManager(TestCase):
    @patch('etcd.Etcd', Mock())
    def setUp(self):
        super(TestEtcdConfigManager, self).setUp()

        self.cm = config_managers.EtcdConfigManager('1.1.1.1:22')
        self.etcd_client = self.cm.etcd_client = Mock()

    def test_set(self):
        self.cm.set('/key', 'value')
        self.etcd_client.set.assert_called_with('key', 'value')

    def test_get(self):
        self.etcd_client.get.return_value = testutils.mock_attr(value='value')
        eq_(self.cm.get('/key'), 'value')
        self.etcd_client.get.assert_called_with('/key')

        def mock_get(key):
            raise KeyError

        self.etcd_client.get = mock_get
        with assert_raises(KeyError):
            self.cm.get('/key')

    def test_delete(self):
        self.cm.delete('/key')
        self.etcd_client.delete.assert_called_with('/key')

    #def test_delete_recursive(self):
    #    raise Exception
    #    #self.cm.delete('/key')
    #    #self.etcd_client.delete.assert_called_with('/key')

    @patch('etcd.Etcd')
    def test_init(self, client):
        cm = config_managers.EtcdConfigManager('1.1.1.1:22')
        client.assert_called_with(host='1.1.1.1', port=22)

        with assert_raises(ValueError):
            cm = config_managers.EtcdConfigManager('')
