from mock import Mock, patch
from nose.tools import assert_in

from stretch import testutils
from stretch.agent import api


class TestApi(testutils.AgentTestCase):
    def test_index(self):
        assert_in('stretch-agent', self.client.get('/').data)

    @patch('stretch.agent.api.NodeListResource.obj_class')
    def test_add_node(self, Node):
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
