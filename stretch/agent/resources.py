import pymongo
from flask.ext.restful import reqparse, Resource, abort

from stretch import utils
from stretch.agent.app import db, api


class PersistentObject(object):
    name = ''
    attrs = {}
    data = {}

    def __init__(self, _id):
        _id = str(_id)
        data = self.get_collection().find_one({'_id': _id})
        if not data:
            self.abort_nonexistent()
        else:
            data['id'] = data.pop('_id')
            self.data = data

    @classmethod
    def create(cls, args):
        args['_id'] = args.pop('id')
        utils.update(args, cls.attrs)
        try:
            cls.get_collection().insert(args)
        except pymongo.errors.DuplicateKeyError as e:
            cls.abort_exists()
        return cls(args['_id'])

    @classmethod
    def abort_nonexistent(cls):
        abort(404, message='%s does not exist' % cls.name.capitalize())

    @classmethod
    def abort_exists(cls):
        abort(409, message='%s already exists' % cls.name.capitalize())

    @classmethod
    def all(cls):
        results = list(cls.get_collection().find())
        for obj in results:
            obj['id'] = obj.pop('_id')
        return {'results': results}

    @classmethod
    def all_objects(cls):
        for obj in cls.get_collection().find(fields=['_id']):
            yield cls(obj['_id'])

    def save(self):
        data = dict(self.data)
        data.pop('id')
        self.update(data)

    def update(self, data):
        _id = self.data.get('id')
        self.get_collection().update({'_id': _id}, {'$set': data}, upsert=True)

    def delete(self):
        self.get_collection().remove({'_id': self.data['id']})
        # TODO: Clean up associated tasks

    @classmethod
    def get_collection(cls):
        return db['%ss' % cls.name]


class ObjectResource(Resource):
    def get(self, _id):
        return self.obj_class(str(_id)).data

    def delete(self, _id):
        self.obj_class(str(_id)).delete()
        return '', 204


class ObjectListResource(Resource):
    def get(self):
        return self.obj_class.all()

    def post(self, arg_parser=None):
        parser = arg_parser or reqparse.RequestParser()
        parser.add_argument('id', type=str, required=True)
        args = parser.parse_args()
        obj = self.obj_class.create(args)
        return obj.data, 201


def get_prefix(plural_name):
    return '/v1/%s' % plural_name


def add_api_resource(plural_name, resource, list_resource):
    prefix = get_prefix(plural_name)
    api.add_resource(list_resource, prefix)
    api.add_resource(resource, '%s/<string:_id>' % prefix)


def add_tasks_resource(resource):
    api.add_resource(resource, get_prefix('tasks'))


def add_task_resource(plural_name, resource):
    prefix = get_prefix(plural_name)
    api.add_resource(resource, '%s/<string:object_id>/tasks' % prefix,
                     endpoint=plural_name)
