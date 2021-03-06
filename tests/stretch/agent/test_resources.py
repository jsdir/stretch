import mongomock
from mock import Mock, patch, call
from unittest import TestCase
from flask.ext.testing import TestCase as FlaskTestCase

from stretch import testutils
from stretch.agent import resources, app


class TestPersistentObject(testutils.AgentTestCase):
    def setUp(self):
        super(TestPersistentObject, self).setUp()

        class Object(resources.PersistentObject):
            name = 'object'

        self.obj_class = Object

    def test_create(self):
        self.obj_class.attrs = {'foo': 'bar'}
        self.obj_class.abort_exists = Mock()
        self.obj_class.abort_nonexistent = Mock()

        obj = self.obj_class.create({'id': 1, 'key': 'value', 'foo': 'foo'})

        data = {'id': '1', 'key': 'value', 'foo': 'bar'}
        self.assertEquals(obj.data, data)
        self.assertEquals(self.obj_class(1).data, data)

        self.obj_class.create({'id': '1', 'key': 'value', 'foo': 'foo'})
        self.obj_class.abort_exists.assert_called_with()

        self.obj_class(2)
        self.obj_class.abort_nonexistent.assert_called_with()

    @patch('stretch.agent.resources.abort')
    def test_aborts(self, abort):
        self.obj = self.obj_class.create({'id': 3, 'bar': 'foo'})
        self.obj.abort_nonexistent()
        abort.assert_called_with(404, message='Object does not exist')
        self.obj.abort_exists()
        abort.assert_called_with(409, message='Object already exists')

    def test_all(self):
        self.obj_class.create({'id': '3', 'bar': 'foo'})
        self.obj_class.create({'id': '4', 'bar': 'foo'})
        self.assertEquals(self.obj_class.all(), {'results': [
            {'id': '3', 'bar': 'foo'}, {'id': '4', 'bar': 'foo'}
        ]})

    def test_all_objects(self):
        objs = [
            self.obj_class.create({'id': '1', 'bar': 'foo'}),
            self.obj_class.create({'id': '2', 'bar': 'foo'})
        ]
        all_objs = list(self.obj_class.all_objects())
        self.assertEquals(all_objs[0].data, {'id': '1', 'bar': 'foo'})
        self.assertEquals(all_objs[1].data, {'id': '2', 'bar': 'foo'})

    def test_save(self):
        self.obj = self.obj_class.create({'id': '3', 'bar': 'foo'})
        self.obj.data['new'] = 'bar'
        self.obj.save()
        obj = self.db.objects.find_one({'_id': '3'})
        self.assertEquals(obj.get('new'), 'bar')

    def test_delete(self):
        self.obj = self.obj_class.create({'id': '3', 'bar': 'foo'})
        self.obj.delete()
        self.assertEquals(self.db.objects.find_one({'_id': '3'}), None)


class TestObjectResource(TestCase):
    def setUp(self):
        obj = self.obj = Mock()

        class ObjectResource(resources.ObjectResource):
            obj_class = obj

        self.resource = ObjectResource()

    def test_get(self):
        self.obj.return_value = testutils.mock_attr(data='foo')
        self.assertEquals(self.resource.get(_id='3'), 'foo')
        self.obj.assert_called_with('3')

    def test_delete(self):
        delete_func = Mock()
        self.obj.return_value = testutils.mock_attr(delete=delete_func)
        self.assertEquals(self.resource.delete(_id='3'), ('', 204))
        delete_func.assert_called_with()


class TestObjectListResource(TestCase):
    def setUp(self):
        obj = self.obj = Mock()

        class ObjectListResource(resources.ObjectListResource):
            obj_class = obj

        self.list_resource = ObjectListResource()

    def test_get(self):
        self.obj.all.return_value = ['data']
        self.assertEquals(self.list_resource.get(), ['data'])

    def test_post(self):
        parser = Mock()
        parser.parse_args.return_value = {'key': 'value'}
        self.obj.create.return_value = testutils.mock_attr(data={'data': '1'})
        self.assertEquals(self.list_resource.post(parser), ({'data': '1'}, 201))
        self.obj.create.assert_called_with({'key': 'value'})
