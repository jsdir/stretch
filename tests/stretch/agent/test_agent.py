import mongomock
from mock import Mock, patch, PropertyMock
from nose.tools import eq_, raises, assert_in
from flask import Flask
from flask.ext.testing import TestCase

from stretch import agent


class AgentTestCase(TestCase):
    def create_app(self):
        agent.app.config['TESTING'] = True
        return agent.app

    def setUp(self):
        agent.db = self.db = mongomock.Connection().db


class TestApi(AgentTestCase):
    def test_index(self):
        rv = self.client.get('/')
        assert_in('stretch-agent', rv.data)


class TestInstance(AgentTestCase):
    def get_instance(self):
        data = {
            '_id': '1',
            'cid': None,
            'node_id': '2',
            'parent_config_key': 'groups/group_id'
        }
        self.db.instances.insert(data)
        return agent.Instance('1')

    def test_get_instances(self):
        rv = self.client.get('/v1/instances')
        self.assertEquals(rv.json, {'results': []})

        data = {
            '_id': '1',
            'cid': None,
            'node_id': '2',
            'parent_config_key': 'groups/group_id'
        }
        self.db.instances.insert(data)
        rv = self.client.get('/v1/instances')
        self.assertEquals(rv.json, {'results': [data]})

    def test_get_instance(self):
        rv = self.client.get('/v1/instances/0')
        self.assertEquals(rv.json, {'message': 'Instance does not exist'})
        self.assertStatus(rv, 404)

        data = {
            '_id': '1',
            'cid': None,
            'node_id': '2',
            'parent_config_key': 'groups/group_id'
        }
        self.db.instances.insert(data)
        rv = self.client.get('/v1/instances/1')
        self.assertEquals(rv.json, data)

    def test_create_instance(self):
        rv = self.client.post('/v1/instances', data={
            'instance_id': '1',
            'node_id': '2',
            'parent_config_key': 'groups/group_id'
        })
        self.assertEquals(rv.json, {
            '_id': '1',
            'cid': None,
            'node_id': '2',
            'parent_config_key': 'groups/group_id'
        })

    def test_should_not_create_duplicate_instance(self):
        self.db.instances.insert({
            '_id': '1',
            'cid': None,
            'node_id': '2',
            'parent_config_key': 'groups/group_id'
        })
        rv = self.client.post('/v1/instances', data={
            'instance_id': '1',
            'node_id': '2',
            'parent_config_key': 'groups/group_id'
        })
        self.assertEquals(rv.json, {'message': 'Instance already exists'})
        self.assertStatus(rv, 409)

    def test_delete_instance(self):
        self.db.instances.insert({'_id': '1', 'cid': None})
        rv = self.client.delete('/v1/instances/1')
        self.assertEquals(rv.data, '')
        self.assertStatus(rv, 204)

    @patch('stretch.agent.Instance.running', new_callable=PropertyMock)
    @patch('stretch.agent.Instance.stop')
    def test_stops_on_delete(self, stop, running):
        instance = self.get_instance()
        running.return_value = True
        instance.delete()
        stop.assert_called_with()

        stop.reset_mock()
        running.return_value = False
        instance.delete()
        assert not stop.called

    @raises(agent.TaskException)
    @patch('stretch.agent.Instance.running', new_callable=PropertyMock)
    def test_should_not_reload_when_stopped(self, running):
        instance = self.get_instance()
        running.return_value = False
        instance.reload()

    @patch('stretch.agent.run_cmd')
    @patch('stretch.agent.Instance.restart')
    @patch('stretch.agent.Instance.running', new_callable=PropertyMock)
    def test_reload(self, running, restart, run_cmd):
        running.return_value = True
        run_cmd.return_value = ('output', 0)
        instance = self.get_instance()
        instance.data['cid'] = 'cid'
        instance.reload()
        run_cmd.assert_called_with(['lxc-attach', '-n', 'cid', '--',
            '/bin/bash', '/usr/share/stretch/files/autoload.sh'])
        assert not restart.called

    @patch('stretch.agent.run_cmd')
    @patch('stretch.agent.Instance.restart')
    @patch('stretch.agent.Instance.running', new_callable=PropertyMock)
    def test_should_restart_when_reload_fails(self, running, restart, run_cmd):
        running.return_value = True
        run_cmd.return_value = ('output', 1)
        instance = self.get_instance()
        instance.data['cid'] = 'cid'
        instance.reload()
        run_cmd.assert_called_with(['lxc-attach', '-n', 'cid', '--',
            '/bin/bash', '/usr/share/stretch/files/autoload.sh'])
        assert restart.called


class TestTask(AgentTestCase):
    def test_get_task(self):
        pass

    def test_create_task(self):
        pass


@patch('stretch.agent.app')
def test_run(app):
    instances = [Mock()]
    with patch('stretch.agent.Instance.get_instances', return_value=instances):
        agent.run()
        assert app.run.called
        instances[0].start.assert_called_with()


@patch('stretch.agent.subprocess')
def test_run_cmd(sub):
    p = Mock()
    p.returncode = 0
    p.communicate.return_value = ('stdout', 'stderr')
    sub.Popen.return_value = p
    eq_(agent.run_cmd(['a', 'b']), ('stdout', 0))
    sub.Popen.assert_called_with(['a', 'b'], stdout=sub.PIPE, stderr=sub.PIPE)
