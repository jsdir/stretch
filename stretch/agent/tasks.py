import uuid
from datetime import datetime
from threading import Thread

from stretch.agent import api, resources, TaskException


class Task(resources.PersistentObject):
    name = 'task'
    attrs = {
        'status': 'PENDING',
        'error': None,
        'started_at': None,
        'ended_at': None
    }

    @classmethod
    def get_object_tasks(cls, object_id, object_type):
        return {'results': list(cls.get_collection().find({
            'object_id': object_id,
            'object_type': object_type
        }))}

    def run(self, func, args, obj):
        self.update({'status': 'RUNNING', 'started_at': datetime.utcnow()})
        try:
            func(obj, args)
        except TaskException as e:
            self.update({'status': 'FAILED', 'error': e.message})
        else:
            self.update({'status': 'FINISHED'})
        self.update({'ended_at': datetime.utcnow()})


# TODO: Lock group tasks across processes; use celery or db
def get_task_resources(obj, tasks):

    class TaskListResource(Resource):
        obj_class = Task

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

    class TaskResource(resources.ObjectResource):
        obj_class = Task

        def get(self, object_id, task_id):
            super(TaskResource, self).get(task_id)

        def delete(self, object_id, task_id):
            super(TaskResource, self).delete(task_id)

    return TaskResource, TaskListResource
