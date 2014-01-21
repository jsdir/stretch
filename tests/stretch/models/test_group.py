from mock import Mock, patch
from unittest import TestCase

from stretch.testutils import patch_settings
from stretch.models import Group


class TestGroup(TestCase):
    def setUp(self):
        self.client = Mock()
        patcher = patch('stretch.agent.supervisors.endpoint_supervisor_client',
            return_value=self.client)
        patcher.start()
        self.addCleanup(patcher.stop)

        for attr in ('group', 'save'):
            self.patch_lb(attr, mock=True)

        self.group = Mock()

        self.lb = self.create_lb()

    def patch_host(self, attr, mock=False):
        patcher = patch('stretch.models.LoadBalancer.%s' % attr)
        if mock:
            mock_obj = patcher.start()
            self.addCleanup(patcher.stop)
            return mock_obj
        else:
            return patcher

    def create_lb(self):
        with self.patch_lb('backend') as backend:
            backend.create_lb.return_value = ('2.2.2.2', 443)
            return LoadBalancer.create(self.group, 'p', 'http', {'k': 'v'})

    def test_create(self):
        lb = self.create_lb()

        lb.group.environment.system.config_manager.set.assert_called_with(
            lb.config_key, '{"host": "2.2.2.2", "port": 443}')
        self.client.add_group.assert_called_with(lb.group.pk,
            lb.group.config_key)
        lb.save.assert_called_with()

    ########
    def test_create_load_balancer(self):
        self.group.create_load_balancer()

    def test_config_key(self):
        config = self.group.environment.system.config_manager
        config.get_group_key.return_value = 'key'
        self.assertEquals(self.group.config_key, 'key')
        config.get_lb_key.assert_called_with(self.group)

    def test_batch_size(self):

        def assert_batch(instances, batch_size):
            self.group.instances.count.return_value = instances
            self.assertEquals(self.group.batch_size, batch_size)

        with patch_settings('STRETCH_BATCH_SIZE', 5):
            assert_batch(1, 1)
            assert_batch(2, 1)
            assert_batch(3, 2)
            assert_batch(4, 2)
            assert_batch(5, 3)
            assert_batch(20, 5)

    """
    def test_add_endpoint(self):
        backend = self.patch_lb('backend', mock=True)
        with self.patch_lb('_apply_endpoint'):
            endpoint = {'host': '1.1.1.1', 'ports': {'http': 80}}
            self.lb.add_endpoint(endpoint)
            self.lb._apply_endpoint.assert_called_with(backend.lb_add_endpoint,
                                                       endpoint)

    def test_remove_endpoint(self):
        backend = self.patch_lb('backend', mock=True)
        with self.patch_lb('_apply_endpoint'):
            endpoint = {'host': '1.1.1.1', 'ports': {'http': 80}}
            self.lb.remove_endpoint(endpoint)
            self.lb._apply_endpoint.assert_called_with(
                backend.lb_remove_endpoint, endpoint)

    def test__apply_endpoint(self):
        endpoint = {'host': '1.1.1.1', 'ports': {'http': 80}}
        func = Mock()

        self.lb.port_name = 'foo'
        self.lb._apply_endpoint(func, endpoint)

        assert not func.called

        self.lb.port_name = 'http'
        self.lb._apply_endpoint(func, endpoint)

        func.assert_called_with(self.lb, '1.1.1.1', 80)

    def test_backend(self):
        self.lb.group.environment.backend = None
        with assert_raises(Exception):
            self.lb.backend
        self.lb.group.environment.backend = 'backend'
        self.assertEquals(self.lb.backend, 'backend')

    def test_config_key(self):
        config = self.lb.group.environment.system.config_manager
        config.get_lb_key.return_value = 'key'
        self.assertEquals(self.lb.config_key, 'key')
        config.get_lb_key.assert_called_with(self.lb)

    def test_pre_delete(self):
        LoadBalancer.pre_delete(Mock(), self.lb)
        self.client.remove_group.assert_called_with(self.lb.group.pk)
        config = self.lb.group.environment.system.config_manager
        config.delete.assert_called_with(self.lb.config_key)
        self.lb.backend.delete_lb.assert_called_with(self.lb)"""
