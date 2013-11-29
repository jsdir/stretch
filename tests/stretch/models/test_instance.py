from mock import Mock, patch
from unittest import TestCase

from stretch.testutils import patch_settings, mock_attr
from stretch.models import Instance


class TestInstance(TestCase):
    def setUp(self):
        for attr in ('environment', 'host', 'node', 'save'):
            patcher = self.patch_instance(attr)
            patcher.start()
            self.addCleanup(patcher.stop)

        self.env = Mock()
        self.node = Mock()
        self.host = mock_attr(nodes=[self.node])

        self.instance = self.create_instance()

    def patch_instance(self, attr):
        return patch('stretch.models.Instance.%s' % attr)

    def create_instance(self):
        return Instance.create(self.env, self.host, self.node)

    def test_create(self):
        with self.patch_instance('sync_node'):
            instance = self.create_instance()
            instance.save.assert_called_with()
            instance.sync_node.assert_called_with(self.node)
            self.host.agent.add_instance.assert_called_with(instance)
            self.assertEquals(instance.environment, self.env)
            self.assertEquals(instance.host, self.host)
            self.assertEquals(instance.node, self.node)

    def test_sync_node_current_release(self):
        node = Mock()
        self.host.nodes = []
        release = Mock()
        self.env.current_release = release
        self.env.using_source = False

        self.instance.sync_node(node)

        self.host.agent.add_node.assert_called_with(node)
        self.host.agent.pull.assert_called_with(node, release=release)

    def test_sync_node_using_source(self):
        node = Mock()
        self.host.nodes = []
        self.env.current_release = None
        self.env.using_source = True

        self.instance.sync_node(node)

        self.host.agent.add_node.assert_called_with(node)
        self.host.agent.pull.assert_called_with(node)

    def test_sync_node_should_not_sync_if_already_deployed(self):
        node = Mock()
        self.host.nodes = [node]

        self.instance.sync_node(node)

        assert not self.host.agent.add_node.called

    def test_reload(self):
        self.instance.reload()
        self.host.agent.reload_instance.assert_called_with(self.instance)

    def test_load_balancer(self):
        self.host.group = None
        self.assertEquals(self.instance.load_balancer, None)

        group = Mock()
        self.host.group = group
        self.assertEquals(self.instance.load_balancer, group.load_balancer)

    def test_config_key(self):
        config = self.instance.environment.system.config_manager
        config.get_instance_key.return_value = 'key'
        self.assertEquals(self.instance.config_key, 'key')
        config.get_instance_key.assert_called_with(self.instance)

    def test_restart(self):
        with self.patch_instance('safe_run'):
            instance = self.create_instance()
            instance.restart()
            restart_instance = self.host.agent.restart_instance
            instance.safe_run.assert_called_with(restart_instance)

    @patch('stretch.models.Instance.pk', 'abc')
    @patch('stretch.models.Instance.load_balancer')
    @patch('stretch.agent.supervisors.endpoint_supervisor_client')
    def test_safe_run(self, client, lb):
        # patch instance.pk = "abc"

        endpoints = client.return_value = Mock()

        with patch.object(self.instance, 'load_balancer', False):
            func = Mock()
            self.instance.safe_run(func)
            func.assert_called_with(self.instance)
            assert not endpoints.block_instance.called
            assert not endpoints.unblock_instance.called

        func.reset_mock()
        config = self.instance.environment.system.config_manager
        config.get.return_value = '{"host": "1.1.1.1", "port": 80}'

        self.instance.safe_run(func)
        func.assert_called_with(self.instance)
        endpoints.block_instance.assert_called_with('abc')
        endpoints.unblock_instance.assert_called_with('abc')
        lb.remove_endpoint.assert_called_with({'host': '1.1.1.1', 'port': 80})

    def test_pre_delete(self):
        with self.patch_instance('safe_run'):
            Instance.pre_delete(Mock(), self.instance)
            remove_instance = self.instance.host.agent.remove_instance
            self.instance.safe_run.assert_called_with(remove_instance)
