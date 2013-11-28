from mock import Mock, patch
from nose.tools import assert_raises
from unittest import TestCase

from stretch.testutils import mock_attr, patch_settings
from stretch.agent.client import AgentClient


class TestClient(TestCase):
    @patch_settings('STRETCH_AGENT_PORT', 1337)
    def setUp(self):
        patcher = patch('stretch.agent.client.requests')
        self.requests = patcher.start()
        self.addCleanup(patcher.stop)

        patcher = patch_settings('STRETCH_AGENT_CERT', '/cert.pem')
        patcher.start()
        self.addCleanup(patcher.stop)

        self.host = mock_attr(address='127.0.0.1')
        self.host.environment = mock_attr(name='env', pk=2)
        self.host.environment.app_paths = {'node': '/path'}
        self.client = AgentClient(self.host)

    def test_add_node(self):
        node = mock_attr(pk=1)
        self.client.add_node(node)
        self.requests.post.assert_called_with(
            'https://127.0.0.1:1337/v1/nodes', data={'id': '1'},
            cert='/cert.pem')

    def test_remove_node(self):
        node = mock_attr(pk=1)
        self.client.remove_node(node)
        self.requests.delete.assert_called_with(
            'https://127.0.0.1:1337/v1/nodes/1', cert='/cert.pem')

    @patch('stretch.agent.client.AgentClient.run_task')
    def test_pull_with_release(self, run_task):
        node = mock_attr(name='node', pk=1)
        node.get_image.return_value = 'image'
        node.ports.all.return_value = [
            mock_attr(name='http', number=80),
            mock_attr(name='https', number=443)
        ]
        release = Mock()
        release.sha = 'sha'

        self.client.pull(node, release)
        run_task.assert_called_with('nodes/1', 'pull', {
            'sha': 'sha',
            'app_path': None,
            'ports': '{"http": 80, "https": 443}',
            'env_id': '2',
            'env_name': 'env',
            'image': 'image'
        })
        node.get_image.assert_called_with(local=False, private=True)

    @patch('stretch.agent.client.AgentClient.run_task')
    def test_pull(self, run_task):
        node = mock_attr(name='node', pk=1)
        node.get_image.return_value = 'image'
        node.ports.all.return_value = [
            mock_attr(name='http', number=80),
            mock_attr(name='https', number=443)
        ]

        self.client.pull(node)
        run_task.assert_called_with('nodes/1', 'pull', {
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
            }, cert='/cert.pem')

    def test_remove_instance(self):
        instance = mock_attr(pk=1)
        self.client.remove_instance(instance)
        self.requests.delete.assert_called_with(
            'https://127.0.0.1:1337/v1/instances/1', cert='/cert.pem')

    @patch('stretch.agent.client.AgentClient.run_task')
    def test_reload_instance(self, run_task):
        instance = mock_attr(pk=1)
        self.client.reload_instance(instance)
        run_task.assert_called_with('instances/1', 'reload')

    @patch('stretch.agent.client.AgentClient.run_task')
    def test_restart_instance(self, run_task):
        instance = mock_attr(pk=1)
        self.client.restart_instance(instance)
        run_task.assert_called_with('instances/1', 'restart')

    @patch('gevent.sleep')
    @patch('stretch.agent.client.AgentClient.task_running')
    def test_run_task(self, task_running, sleep):

        class TestException(Exception):
            pass

        sleep.side_effect = TestException()
        response = Mock()
        response.json.return_value = {'id': '2'}
        self.requests.post.return_value = response

        with assert_raises(TestException):
            self.client.run_task('a/1', 'reload', {'k': 'v'})

        self.requests.post.assert_called_with(
            'https://127.0.0.1:1337/v1/a/1/tasks',
            data={'k': 'v'},
            cert='/cert.pem'
        )
        task_running.assert_called_with('https://127.0.0.1:1337/v1/tasks/2')

    def test_task_running(self):
        response = Mock()
        response.json.return_value = {'status': 'FINISHED'}
        self.requests.get.return_value = response
        result = self.client.task_running('https://s/v1/tasks/2')
        self.requests.get.assert_called_with('https://s/v1/tasks/2',
                                             cert='/cert.pem')
        self.assertEquals(result, False)

        response = Mock()
        response.json.return_value = {'status': 'RUNNING'}
        self.requests.get.return_value = response
        result = self.client.task_running('https://s/v1/tasks/2')
        self.assertEquals(result, True)

        response = Mock()
        response.json.return_value = {'status': 'FAILED'}
        self.requests.get.return_value = response
        with assert_raises(Exception):
            self.client.task_running('https://s/v1/tasks/2')
