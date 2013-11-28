from mock import Mock, patch
from nose.tools import assert_in

from stretch import testutils
from stretch.agent import api


class TestApi(testutils.AgentTestCase):
    def test_index(self):
        assert_in('stretch-agent', self.client.get('/').data)

    @patch('stretch.agent.api.NodeListResource.obj_class')
    def test_add_node(self, Node):
        Node.create.return_value = testutils.mock_attr(data={})
        self.client.post('/v1/nodes', data={'id': '1'})
        Node.create.assert_called_with({'id': '1'})

    @patch('stretch.agent.api.NodeResource.obj_class')
    def test_remove_node(self, Node):
        node = Node.return_value = Mock()

        self.client.delete('/v1/nodes/1')

        Node.assert_called_with('1')
        node.delete.assert_called_with()

    @patch('stretch.agent.api.InstanceListResource.obj_class')
    def test_add_instance(self, Instance):
        Instance.create.return_value = testutils.mock_attr(data={})
        self.client.post('/v1/instances', data={
            'node_id': '2',
            'config_key': '/key',
            'id': '1',
            'host_name': 'host_name'
        })
        Instance.create.assert_called_with({
            'node_id': '2',
            'config_key': '/key',
            'id': '1',
            'host_name': 'host_name'
        })

    @patch('stretch.agent.api.InstanceResource.obj_class')
    def test_remove_instance(self, Instance):
        instance = Instance.return_value = Mock()

        self.client.delete('/v1/instances/1')

        Instance.assert_called_with('1')
        instance.delete.assert_called_with()


    @patch('stretch.agent.objects.Node')
    def test_pull(self, Node):
        r = self.client.post('/v1/nodes/1/tasks', data={
            'sha': None,
            'app_path': '/path',
            'ports': '{"http": 80, "https": 443}',
            'env_id': '2',
            'env_name': 'env',
            'image': 'image',
            'task': 'pull'
        })
        raise Exception(r.data)
        #raise Exception(dir(self.create_app()))

        Node.pull.assert_called_with()

    '''
    def test_reload_instance(self):
        self.client.post('/v1/instances/1/tasks', data={
            'task': 'reload',
        })

    def test_restart_instance(self):
        self.client.post('/v1/instances/1/tasks', data={
            'task': 'restart',
        })

    def test_run_task(self):
        self.client.get('/v1/tasks/2')'''
