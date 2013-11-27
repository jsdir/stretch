from flask.ext.restful import reqparse

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


resources.add_api_resource('instances', InstanceResource, InstanceListResource)
resources.add_api_resource('nodes', NodeResource, NodeListResource)

"""
def restart_instance(instance, args):
    instance.restart()


def reload_instance(instance, args):
    instance.reload()


resources.add_api_resource('instances', InstanceResource, InstanceListResource)
resources.add_task_resource('instances', Instance, {
    'restart': {'task': restart_instance},
    'reload': {'task': reload_instance},
})
"""


# TODO: Lock group tasks across processes; use celery or db
def get_task_resources(obj, tasks):

    class TaskListResource(Resource):
        obj_class = objects.Task

        def get(self, object_id):
            return self.obj_class.get_object_tasks(object_id, obj.name)

        def post(self, object_id):
            names = tasks.values()
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

            task = Task.create({
                'id': str(uuid.uuid4()),
                'object_id': object_id,
                'object_name': obj.name
            })

            Thread(target=task.run(task_func, task_args,
                                   obj(object_id))).start()
            return task.data, 201

    class TaskResource(ObjectResource):
        obj_class = objects.Task

        def get(self, object_id, task_id):
            super(TaskResource, self).get(task_id)

        def delete(self, object_id, task_id):
            super(TaskResource, self).delete(task_id)

    return TaskResource, TaskListResource


def configure_parser(parser):
    parser.add_argument('sha', type=str)
    parser.add_argument('app_path', type=str)
    parser.add_argument('ports', type=str, required=True)
    parser.add_argument('env_id', type=str, required=True)
    parser.add_argument('env_name', type=str, required=True)
    parser.add_argument('image', type=str, required=True)


def verify_args(args):
    args['ports'] = json.loads(args['ports'])
    if not args['sha'] and not args['sha']:
        raise Exception('neither `sha` nor `app_path` was specified')


def pull(node, args):
    args['ports'] = json.loads(args['ports'])
    node.pull(args)


# Implement long running tasks; decided

"""
resources.add_api_resource('nodes', NodeResource, NodeListResource)
resources.add_task_resource('nodes', Node, {
    'pull': {
        'parser_config': configure_parser,
        'verify_args': verify_args,
        'task': pull
    }
})
"""
