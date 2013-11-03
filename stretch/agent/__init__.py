import os
import uuid
import subprocess
import pymongo
from threading import Thread
from datetime import datetime

from flask import Flask, jsonify
from flask.ext.restful import reqparse, abort, Api, Resource, marshal_with


db = pymongo.MongoClient()['stretch-agent']
app = Flask(__name__)
api = Api(app, catch_all_404s=True)
container_dir = '/usr/share/stretch'
task_groups = {}


class TaskException(Exception):
    pass


class PersistentObject(object):
    def __init__(self, _id):
        self.data = self.get_collection().find_one({'_id': _id})
        if not self.data:
            self.abort_nonexistent()

    @classmethod
    def abort_nonexistent(cls):
        abort(404, message='%s does not exist' % cls.name.capitalize())

    @classmethod
    def abort_exists(cls):
        abort(409, message='%s already exists' % cls.name.capitalize())

    def save(self):
        self.update(self.data)

    def update(self, data):
        _id = self.data['_id']
        self.get_collection().update({'_id': _id}, {'$set': data}, upsert=True)

    def delete(self):
        self.get_collection().remove({'_id': self.data['_id']})

    @classmethod
    def get_collection(cls):
        return db['%ss' % cls.name]


class Instance(PersistentObject):
    name = 'instance'

    @classmethod
    def create(cls, instance_id, node_id, config_key):
        try:
            cls.get_collection().insert({
                '_id': instance_id,
                'cid': None,
                'node_id': node_id,
                'parent_config_key': config_key
            })
        except pymongo.errors.DuplicateKeyError as e:
            cls.abort_exists()
        return cls(instance_id)

    def delete(self):
        if self.running:
            self.stop()
        super(Instance, self).delete()

    @classmethod
    def all(cls):
        return {'results': list(cls.get_collection().find())}

    def reload(self):
        if not self.running:
            raise TaskException('container is not running')

        code = run_cmd(['lxc-attach', '-n', self.data['cid'], '--',
                        '/bin/bash', os.path.join(container_dir, 'files',
                        'autoload.sh')])[1]

        if code != 0:
            # No user-defined autoload.sh or script wants to reload; restart.
            self.restart()

    def restart(self):
        self.stop()
        self.start()

    def start(self):
        if self.running:
            raise TaskException('container is already running')

        node = self.get_node()
        if not node:
            raise TaskException("container's node does not exist")
        if not node.pulled: # Has sha or app_path
            raise TaskException("container's node has not been pulled yet")

        # Run container
        cmd = ['docker', 'run', '-d'] + self.get_run_args(node)
        self.data['cid'] = run_cmd(cmd)[0].strip()
        self.save()

        # Update ports
        # TODO

    def stop(self):
        if not self.running:
            raise TaskException('container is already stopped')

        run_cmd(['docker', 'stop', self.data['cid']])
        self.data['cid'] = None
        self.save()

    def get_node(self):
        if self.data['node_id']:
            return Node(self.data['node_id'])
        return None

    @staticmethod
    def get_run_args(node):
        mounts = ['-v', '%s:%s:ro' % (self.get_templates_path(),
            os.path.join(container_dir, 'templates'))]
        if node.data['app_path']:
            mounts += ['-v', '%s:%s:ro' % (node.data['app_path'],
                os.path.join(container_dir, 'app'))]
        return mounts

    @classmethod
    def start_all(cls):
        [instance.start() for instance in cls.get_instances()]

    @classmethod
    def get_instances(cls):
        for instance in self.collection.find(fields=['_id']):
            yield cls(instance['_id'])

    @property
    def running(self):
        return self.data['cid'] != None


class Task(PersistentObject):
    name = 'task'

    @classmethod
    def create(cls, task_id, task_type, instance_id):
        try:
            self.collection.insert({
                '_id': task_id,
                'type': task_type,
                'instance_id': instance_id,
                'status': 'PENDING',
                'error': None,
                'started_at': None,
                'ended_at': None
            })
        except pymongo.errors.DuplicateKeyError as e:
            self.abort_exists()
        return cls(task_id)


class Node(PersistentObject):
    name = 'node'

    @classmethod
    def create(cls, node_id, env_id, env_name):
        try:
            self.collection.insert({
                '_id': node_id,
                'env_id': env_id,
                'env_name': env_name,
                'app_path': None,
                'sha': None,
                'ports': {},
                'image': None
            })
        except pymongo.errors.DuplicateKeyError as e:
            self.abort_exists()
        return cls(node_id)

    def pull(self, sha=None, app_path=None, ):
        self.derp

    @property
    def pulled(self):
        return self.data['sha'] or self.data['app_path']


class InstanceListResource(Resource):
    def get(self):
        return Instance.all()

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('instance_id', type=str, required=True,
                            dest='instance_id')
        parser.add_argument('node_id', type=str, required=True)
        parser.add_argument('parent_config_key', type=str, required=True)
        args = parser.parse_args()

        instance = Instance.create(args['instance_id'], args['node_id'],
                                   args['parent_config_key'])

        return instance.data, 201


class InstanceResource(Resource):
    def get(self, instance_id):
        return Instance(instance_id).data

    def delete(self, instance_id):
        Instance(instance_id).delete()
        return '', 204


class TaskListResource(Resource):
    def post(self, instance_id):
        parser = reqparse.RequestParser()
        parser.add_argument('type', type=str, required=True, choices=(
                            'start', 'stop', 'restart', 'reload'))

        task_id = str(uuid.uuid4())
        task = Task.create(task_id, task_type, instance_id)
        running = run_task(task_id, args['type'], instance)

        if running:
            task.update({'status': 'RUNNING', 'started_at': datetime.utcnow()})

        return task.data, 201


class TaskResource(Resource):
    def get(self, instance_id, task_id):
        return Task(task_id).to_json()


# TODO: Lock group tasks across processes; use message queue or db
def run_task(task_id, func, group=None, *args, **kwargs):
    task = Task(task_id)

    if group in task_groups:
        tasks = task_groups[group]
    else:
        tasks = task_groups[group] = {}

    def callback():
        task.update({'status': 'RUNNING', 'started_at': datetime.utcnow()})

        error = None
        try:
            func(*args, **kwargs)
        except TaskException as e:
            error = e.message

        task.update({'ended_at': datetime.utcnow()})

        # Process task results
        if error:
            task.update({'status': 'FAILED', 'error': error})
        else:
            task.update({'status': 'FINISHED'})

        # Continue processing tasks or clean up
        tasks.pop(task_id, None)
        if tasks:
            # Run next task in queue
            tasks.values()[0].start()
        else:
            # Delete the task group
            task_groups.pop(group, None)

    func_thread = Thread(target=callback)
    tasks[task_id] = func_thread

    if tasks:
        # Task has to wait
        return False
    else:
        # Task is immediately started
        func_thread.start()
        return True


def run_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    return stdout, p.returncode


def run():
    Instance.start_all()
    app.run(debug=True)


@app.route('/')
def index():
    return 'stretch-agent'


api.add_resource(InstanceListResource, '/v1/instances')
api.add_resource(InstanceResource, '/v1/instances/<string:instance_id>')
api.add_resource(TaskListResource, '/v1/instances/<string:instance_id>/tasks',
                 '/v1/tasks')
api.add_resource(TaskResource,
                 '/v1/instances/<string:instance_id>/tasks/<string:task_id>')


def pull(registry_url, sha=None):
    # not called when using app path
    nodes = []
    for instance in Instance.get_instances():
        node = instance.get_node()
        if node not in nodes:
            nodes.append(node)

    for node in nodes:
        if sha:
            base = registry_url
            image = '%s/sys%s/%s' % (registry_url, node.sys_id, node.name)
        else:
            base = 'stretch_agent'
        image = 'stretch_agent/sys%s/%s' % (base, node.sys_id, node.name)
        #image = ''node.sys_id, node.env_id, 
        #run_cmd(['docker', 'pull', node.image_url])

        #templates / nodes / {node_id, node_id} <- unrendered templates
        #/ intances / instance_id  <- rendered templates
