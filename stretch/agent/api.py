import json
import uuid
from threading import Thread
from flask.ext.restful import reqparse, Resource

from stretch.agent.app import app
from stretch.agent import objects, resources


# bind objects to flask app
@app.route('/')
def index():
    return 'stretch-agent'


class InstanceResource(resources.ObjectResource):
    obj_class = objects.Instance


class InstanceListResource(resources.ObjectListResource):
    obj_class = objects.Instance

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('node_id', type=str, required=True)
        parser.add_argument('host_name', type=str, required=True)
        parser.add_argument('config_key', type=str, required=True)
        super(InstanceListResource, self).post(parser)


class NodeResource(resources.ObjectResource):
    obj_class = objects.Node


class NodeListResource(resources.ObjectListResource):
    obj_class = objects.Node


class TaskListResource(Resource):
    def get(self, _id):
        return objects.Task(str(_id)).data


def get_task_list(obj, tasks):

    class ObjectTaskListResource(Resource):
        def post(self, object_id):
            names = tasks.keys()
            parser = reqparse.RequestParser()
            parser.add_argument('task', type=str, required=True, choices=names)
            args = parser.parse_args()
            task = tasks[args['task']]

            parser_config = task.get('parser_config')
            task_args = args
            if parser_config:
                task_parser = reqparse.RequestParser()
                parser_config(task_parser)
                task_args = task_parser.parse_args()
            task_args.pop('task', None)

            verify_args = task.get('verify_args')
            if verify_args:
                verify_args(task_args)

            task_func = task.get('task')
            if not task_func:
                raise TaskException('no task defined')

            task = objects.Task.create({
                'id': str(uuid.uuid4()),
                'object_id': object_id,
                'object_name': obj.name
            })
            Thread(target=task.run(task_func, task_args,
                                   obj(int(object_id)))).start()
            return task.data, 201

    return ObjectTaskListResource


def restart_instance(instance, args):
    instance.restart()


def reload_instance(instance, args):
    instance.reload()


def configure_parser(parser):
    parser.add_argument('sha', type=str)
    parser.add_argument('app_path', type=str)
    parser.add_argument('ports', type=str, required=True)
    parser.add_argument('env_id', type=str, required=True)
    parser.add_argument('env_name', type=str, required=True)
    parser.add_argument('image', type=str, required=True)


def verify_args(args):
    args['ports'] = json.loads(args['ports'])
    if not args['sha'] and not args['app_path']:
        raise Exception('neither `sha` nor `app_path` was specified')


def pull(node, args):
    raise Exception(args)
    args['ports'] = json.loads(args['ports'])
    node.pull(args)


resources.add_api_resource('instances', InstanceResource, InstanceListResource)
resources.add_api_resource('nodes', NodeResource, NodeListResource)
resources.add_task_resource('instances', get_task_list(objects.Instance, {
    'restart': {'task': restart_instance},
    'reload': {'task': reload_instance}
}))
resources.add_task_resource('nodes', get_task_list(objects.Node, {
    'pull': {
        'parser_config': configure_parser,
        'verify_args': verify_args,
        'task': pull
    }
}))
resources.add_tasks_resource(TaskListResource)

# TODO: Lock group tasks across processes; use celery or db
