import os
import json
import uuid
from datetime import datetime
from flask.ext.restful import reqparse

from stretch import utils, config_managers
from stretch.agent.app import TaskException, agent_dir, api
from stretch.agent import resources


class Instance(resources.PersistentObject):
    name = 'instance'
    attrs = {'cid': None, 'endpoint': None}

    def __init__(self, *args, **kwargs):
        self.config_manager = config_managers.EtcdConfigManager(
                              '127.0.0.1:4001')
        try:
            self.agent_host = os.environ['AGENT_HOST']
        except KeyError:
            raise Exception('"AGENT_HOST" environment variable not set')
        super(Instance, self).__init__(*args, **kwargs)

    @classmethod
    def create(cls, args):
        super(Instance, self).create(args)
        # TODO: have start/stop behave as individual tasks, use HTTP request
        # blocking
        self.start()

    def delete(self):
        if self.running:
            self.stop()
        super(Instance, self).delete()

    def reload(self):
        if not self.running:
            raise TaskException('container is not running')

        code = utils.run_cmd(['lxc-attach', '-n', self.data['cid'], '--',
                        '/bin/bash', os.path.join(container_dir, 'files',
                        'autoload.sh')], allow_errors=True)[1]

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
        if not node.pulled:
            raise TaskException("container's node has not been pulled yet")

        # Compile templates for new run
        self.compile_templates(node)

        # Run container
        cmd = ['docker', 'run', '-d'] + self.get_run_args(node)
        cid = utils.run_cmd(cmd)[0].strip()

        # Get ports
        ports = {}
        for name, port in self.data['ports'].iteritems():
            # TODO: Use API when it can handle port mapping
            host = utils.run_cmd(['docker', 'port', cid, str(port)])
            ports[name] = int(host.split(':')[1])

        self.data['cid'] = cid
        self.data['endpoint'] = json.dumps({
            'host': self.agent_host, 'ports': ports
        })
        self.save()

    def stop(self):
        if not self.running:
            raise TaskException('container is already stopped')

        # Remove from config
        self.config_manager.delete(self.data['config_key'])

        # Stop container
        utils.run_cmd(['docker', 'stop', self.data['cid']])
        self.data['cid'] = None
        self.data['endpoint'] = None
        self.save()

    def set_endpoint(self):
        self.config_manager.set(self.data['config_key'], self.data['endpoint'])

    def get_node(self):
        if self.data['node_id']:
            return nodes.Node(self.data['node_id'])
        return None

    def get_run_args(self, node):
        mounts = ['-v', '%s:%s:ro' % (self.get_templates_path(),
            os.path.join(container_dir, 'templates'))]
        if node.data['app_path']:
            mounts += ['-v', '%s:%s:ro' % (node.data['app_path'],
                os.path.join(container_dir, 'app'))]
        return mounts

    def get_templates_path(self):
        return os.path.join(agent_dir, 'templates', 'instances',
                            self.data['_id'])

    def compile_templates(self, node):
        templates_path = self.get_templates_path()

        # Remove all contents before adding new templates
        utils.clear_path(templates_path)

        # Walk through node templates, render, and save to instance templates.
        node_templates_path = node.get_templates_path()
        if os.path.exists(node_templates_path):
            for dirpath, dirnames, filenames in os.walk(node_templates_path):
                rel_dir = os.path.relpath(dirpath, node_templates_path)
                for file_name in filenames:
                    self.compile_template(os.path.normpath(os.path.join(
                        rel_dir, file_name)), node_templates_path,
                        templates_path, node)

    def compile_template(self, rel_path, src, dest, node):
        src_path = os.path.join(src, rel_path)
        dest_path, ext = os.path.splitext(os.path.join(dest, rel_path))

        # Remove .jinja extension
        ext = ext.lower()
        if ext != '.jinja':
            dest_path += ext

        # Ensure container folder exists
        utils.makedirs(os.path.split(dest_path)[0])

        context = {
            'env_name': self.node.data['env_name'],
            'host_name': self.data['host_name'],
            'instance_id': self.data['_id'],
            'release': self.node.data['sha']
        }

        utils.render_template_to_file(src_path, dest_path, [context])

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


class InstanceListResource(resources.ObjectListResource):
    obj_class = Instance

    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('node_id', type=str, required=True)
        parser.add_argument('host_name', type=str, required=True)
        parser.add_argument('config_key', type=str, required=True)
        super(InstanceListResource, self).post(parser)


class InstanceResource(resources.ObjectResource):
    obj_class = Instance


def restart_instance(instance, args):
    instance.restart()


def reload_instance(instance, args):
    instance.reload()


"""
resources.add_api_resource('instances', InstanceResource, InstanceListResource)
resources.add_task_resource('instances', Instance, {
    'restart': {'task': restart_instance},
    'reload': {'task': reload_instance},
})"""


class LoadBalancer(resources.PersistentObject):
    name = 'loadbalancer'

    @classmethod
    def create(cls, args):
        super(LoadBalancer, self).create(args)
        self.start()

    def delete(self):
        db.endpoints.remove({'lb_id': self.data['_id']})
        self.stop()
        super(Instance, self).delete()

    def start(self):
        get_client().start_lb(self.data['_id'])

    def stop(self):
        get_client().stop_lb(self.data['_id'])

    @classmethod
    def start_all(cls):
        [lb.start() for lb in cls.get_lbs()]

    @classmethod
    def get_lbs(cls):
        for lb in self.collection.find(fields=['_id']):
            yield cls(lb['_id'])


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

    class TaskResource(ObjectResource):
        obj_class = Task

        def get(self, object_id, task_id):
            super(TaskResource, self).get(task_id)

        def delete(self, object_id, task_id):
            super(TaskResource, self).delete(task_id)

    return TaskResource, TaskListResource


class Node(resources.PersistentObject):
    name = 'node'
    attrs = {
        'env_id': None,
        'env_name': None,
        'app_path': None,
        'sha': None,
        'ports': {},
        'image': None
    }

    def pull(self, args):
        # TODO: accept an id argument and automatically create node if that is
        # supplied with the pull request.
        # Pull image
        if not args['app_path']:
            utils.run_cmd(['docker', 'pull', args['image']])
        # Pull templates
        templates_path = self.get_templates_path()
        src = 'salt://templates/%s/%s' % (args['env_id'], self.data['_id'])
        caller_client().function('cp.get_dir', src, templates_path)
        # Remove all contents before adding new templates
        utils.clear_path(templates_path)
        node.update(args)

    def get_templates_path(self):
        return os.path.join(agent_dir, 'templates', 'nodes', self.data['_id'])

    def delete(self):
        # TODO: delete all docker images
        super(Node, self).delete()

    @property
    def pulled(self):
        return self.data['sha'] or self.data['app_path']


class NodeResource(resources.ObjectResource):
    obj_class = Node


class NodeListResource(resources.ObjectListResource):
    obj_class = Node


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
