import mongomock
from mock import Mock, patch
from unittest import TestCase

from stretch.agent import resources, app


class TestPersistentObject(TestCase):
    def setUp(self):
        self.db = resources.db = mongomock.Connection().db

        class Object(resources.PersistentObject):
            name = 'object'
            attrs = {'foo': 'bar', 'key': 'value'}

        self.obj_class = Object
        self.obj = self.obj_class.create({'id': 3, 'foo': 'foo'})

    def test_create(self):
        self.obj_class.abort_exists = Mock()
        self.obj_class.abort_nonexistent = Mock()

        obj = self.obj_class.create({'id': 1, 'key': 'value', 'foo': 'foo'})

        data = {'id': 1, 'key': 'value', 'foo': 'bar'}
        self.assertEquals(obj.data, data)
        self.assertEquals(self.obj_class(1).data, data)

        self.obj_class.create({'id': 1, 'key': 'value', 'foo': 'foo'})
        self.obj_class.abort_exists.assert_called_with()

        self.obj_class(2)
        self.obj_class.abort_nonexistent.assert_called_with()

    @patch('stretch.agent.resources.abort')
    def test_aborts(self, abort):
        self.obj.abort_nonexistent()
        abort.assert_called_with(404, message='Object does not exist')
        self.obj.abort_exists()
        abort.assert_called_with(409, message='Object already exists')

    def test_all(self):
        pass
