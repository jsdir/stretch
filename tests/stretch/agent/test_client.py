from mock import Mock, patch
from unittest import TestCase

from stretch.testutils import mock_attr, patch_settings
from stretch.agent.client import AgentClient


class TestClient(TestCase):
    @patch_settings('STRETCH_AGENT_PORT', 1337)
    def setUp(self):
        patcher = patch('stretch.agent.client.requests')
        self.requests = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch('stretch.agent.client.AgentClient.run_task')
        self.run_task = patcher.start()
        self.addCleanup(patcher.stop)

        self.requests
        self.host = mock_attr(address='127.0.0.1')
        self.host.environment = mock_attr(name='env', pk=2)
        self.host.environment.app_paths = {'node': '/path'}
        self.client = AgentClient(self.host)

    def test_pull_with_release(self):
        node = mock_attr(name='node', pk=1)
        node.get_image.return_value = 'image'
        node.ports.all.return_value = [
            mock_attr(name='http', number=80),
            mock_attr(name='https', number=443)
        ]
        release = Mock()
        release.sha = 'sha'

        self.client.pull(node, release)
        self.run_task.assert_called_with('nodes/1', 'pull', {
            'sha': 'sha',
            'app_path': None,
            'ports': '{"http": 80, "https": 443}',
            'env_id': '2',
            'env_name': 'env',
            'image': 'image'
        })
        node.get_image.assert_called_with(local=False, private=True)

    def test_pull(self):
        node = mock_attr(name='node', pk=1)
        node.get_image.return_value = 'image'
        node.ports.all.return_value = [
            mock_attr(name='http', number=80),
            mock_attr(name='https', number=443)
        ]

        self.client.pull(node)
        self.run_task.assert_called_with('nodes/1', 'pull', {
            'sha': None,
            'app_path': '/path',
            'ports': '{"http": 80, "https": 443}',
            'env_id': '2',
            'env_name': 'env',
            'image': 'image'
        })
        node.get_image.assert_called_with(local=True)

    def test_add_instance(self):
        instance = mock_attr(pk=1)
        instance.node.pk = 2
        instance.host.name = 'host_name'
        instance.config_key = '/key'
        self.client.add_instance(instance)
        self.requests.post.assert_called_with(
            'https://127.0.0.1:1337/v1/instances', data={
                'node_id': '2',
                'config_key': '/key',
                'id': '1',
                'host_name': 'host_name'
        })

    def test_remove_instance(self):
        instance = mock_attr(pk=1)
        self.client.remove_instance(instance)
        self.requests.delete.assert_called_with(
            'https://127.0.0.1:1337/v1/instances/1')

    def test_reload_instance(self):
        instance = mock_attr(pk=1)
        self.client.reload_instance(instance)
        self.run_task.assert_called_with('instances/1', 'reload')

    def test_restart_instance(self):
        instance = mock_attr(pk=1)
        self.client.restart_instance(instance)
        self.run_task.assert_called_with('instances/1', 'restart')
