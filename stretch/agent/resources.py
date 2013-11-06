import pymongo
from flask.ext.restful import reqparse, Resource

from stretch import utils
from stretch.agent import db, api, tasks


class PersistentObject(object):
    attrs = {}

    def __init__(self, _id):
        self.data = self.get_collection().find_one({'_id': _id})
        if not self.data:
            self.abort_nonexistent()

    @classmethod
    def create(cls, args):
        args['_id'] = args.pop('id')
        utils.update(args, self.attrs)
        try:
            self.collection.insert(args)
        except pymongo.errors.DuplicateKeyError as e:
            self.abort_exists()
        return cls(args['_id'])

    @classmethod
    def abort_nonexistent(cls):
        abort(404, message='%s does not exist' % cls.name.capitalize())

    @classmethod
    def abort_exists(cls):
        abort(409, message='%s already exists' % cls.name.capitalize())

    @classmethod
    def all(cls):
        return {'results': list(cls.get_collection().find())}

    def save(self):
        self.update(self.data)

    def update(self, data):
        _id = self.data['_id']
        self.get_collection().update({'_id': _id}, {'$set': data}, upsert=True)

    def delete(self):
        self.get_collection().remove({'_id': self.data['_id']})
        # Clean up tasks
        for task in tasks.Task.get_object_tasks(self.data['_id'], self.name):
            tasks.Task(task['_id']).delete()

    @classmethod
    def get_collection(cls):
        return db['%ss' % cls.name]


class ObjectListResource(Resource):
    def get(self):
        return self.obj_class.all()

    def post(self, arg_parser=None):
        parser = arg_parser or reqparse.RequestParser()
        parser.add_argument('id', type=str, required=True)
        args = parser.parse_args()
        obj = self.obj_class.create(args)
        return obj.data, 201


class ObjectResource(Resource):
    def get(self, _id):
        return self.obj_class(_id).data

    def delete(self, _id):
        self.obj_class(_id).delete()
        return '', 204


def add_api_resource(resource, list_resource, plural_name):
    prefix = '/v1/%s' % plural_name
    api.add_resource(list_resource, prefix)
    api.add_resource(resource, '%s/<string:_id>' % prefix)


def add_task_resource(plural_name, obj, tasks):
    resource, resource_list = tasks.get_task_resources(obj, tasks)
    prefix = '/v1/%s' % plural_name
    api.add_resource(resource_list, '%s/<string:_id>/tasks' % prefix)
    api.add_resource(resource,
                     '%s/<string:_id>/tasks/<string:task_id>' % prefix)
