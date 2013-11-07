import os
from flask.ext.restful import reqparse

from stretch import utils, config_managers
from stretch.agent import resources, TaskException, nodes


config_manager = config_managers.EtcdConfigManager('127.0.0.1:4001')


class Instance(resources.PersistentObject):
    name = 'instance'
    attrs = {'cid': None}

    @classmethod
    def create(cls, args):
        super(Instance, self).create(args)
        # TODO: have start/stop behave as individual tasks
        self.start()

    def delete(self):
        if self.running:
            self.stop()
        super(Instance, self).delete()

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
        if not node.pulled:
            raise TaskException("container's node has not been pulled yet")

        # Compile templates for new run
        self.compile_templates()

        # Run container
        cmd = ['docker', 'run', '-d'] + self.get_run_args(node)
        self.data['cid'] = run_cmd(cmd)[0].strip()
        self.save()

        # Get ports
        ports = {}
        for name, port in self.data['ports'].iteritems():
            # TODO: Use API when it can handle port mapping
            host = run_cmd(['docker', 'port', self.data['cid'], str(port)])
            ports[name] = int(host.split(':')[1])

        # Add to config
        config_manager.set_dict('%s/ports' % self.data['config_key'], ports)

    def stop(self):
        if not self.running:
            raise TaskException('container is already stopped')

        # Remove from config
        config_manager.delete(self.data['config_key'])

        # Stop container
        run_cmd(['docker', 'stop', self.data['cid']])
        self.data['cid'] = None
        self.save()

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
        return os.path.join(agent_dir, 'templates', self.data['_id'])

    def compile_templates(self):
        node = self.get_node()
        if not node:
            raise TaskException("container's node does not exist")
        templates_path = self.get_templates_path()

        # Remove all contents before adding new templates
        utils.clear_path(templates_path)

        # Walk through node templates, render, and save to instance templates.
        node_templates_path = self.get_node().get_templates_path()
        for dirpath, dirnames, filenames in os.walk(node_templates_path):
            rel_dir = os.path.relpath(dirpath, node_templates_path)
            for file_name in filenames:
                self.compile_template(os.path.normpath(os.path.join(rel_dir,
                    file_name)), node_templates_path, templates_path, node)

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


resources.add_api_resource('instances', InstanceResource, InstanceListResource)
resources.add_task_resource('instances', Instance, {
    'restart': {'task': restart_instance},
    'reload': {'task': reload_instance},
})
