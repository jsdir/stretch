import os
import json
import uuid
from datetime import datetime

from stretch import utils, config_managers
from stretch.agent.app import TaskException, agent_dir, container_dir
from stretch.agent import resources


class Instance(resources.PersistentObject):
    name = 'instance'
    attrs = {'cid': None, 'endpoint': None}

    @classmethod
    def create(cls, args):
        super(Instance, cls).create(args)
        # TODO: have start/stop behave as individual tasks, use HTTP request
        # Attempt to start,
        try:
            # Attempt to start, but don't fail if the node isn't ready
            cls.start()
        except TaskException:
            pass

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
            log.info('container is already running')
            return

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
            log.info('container is already stopped')
            return

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
            return Node(self.data['node_id'])
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
        [instance.start() for instance in cls.all_objects()]

    @property
    @utils.memoized
    def agent_host(self):
        try:
            return os.environ['AGENT_HOST']
        except KeyError:
            raise TaskException('"AGENT_HOST" environment variable not set')

    @property
    @utils.memoized
    def config_manager(self):
        return config_managers.EtcdConfigManager('127.0.0.1:4001')

    @property
    def running(self):
        return self.data['cid'] != None


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
        # Pull image
        if not args['app_path']:
            utils.run_cmd(['docker', 'pull', args['image']])

        # Prepare to pull templates
        templates_path = self.get_templates_path()
        src = 'salt://templates/%s/%s' % (args['env_id'], self.data['_id'])

        # Remove all contents before adding new templates
        utils.clear_path(templates_path)

        # Pull templates
        caller_client().function('cp.get_dir', src, templates_path)

        node.update(args)

    def get_templates_path(self):
        return os.path.join(agent_dir, 'templates', 'nodes', self.data['_id'])

    def delete(self):
        # TODO: delete all docker images
        super(Node, self).delete()

    @property
    def pulled(self):
        return (self.data['sha'] != None) or (self.data['app_path'] != None)


class LoadBalancer(resources.PersistentObject):
    name = 'loadbalancer'

    @classmethod
    def create(cls, _id):
        lb = super(LoadBalancer, cls).create({'id': _id})
        lb.start()
        return lb

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
        [lb.start() for lb in cls.all_objects()]


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
