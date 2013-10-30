import os
import errno
import json
import docker
import pymongo
import shutil
import tempfile
from contextlib import contextmanager
import jinja2
from subprocess import call, Popen
import logging
import etcd

log = logging.getLogger(__name__)
etcd_client = etcd.Client()
docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.5')
mongo_client = pymongo.MongoClient()
db = mongo_client['stretch-agent']
agent_dir = '/var/lib/stretch/agent'
container_dir = '/usr/share/stretch'


class Instance(object):
    def __init__(self, instance_id):
        self.id = instance_id
        self.data = {}
        self.load()

    def load(self):
        # Attempt to load instance attributes from redis
        data = db.instances.find_one({'id': self.id})
        if data:
            self.data['env_id'] = data['env_id']
            self.data['node_id'] = data['node_id']
            self.data['instance_key'] = data['instance_key']
            self.data['cid'] = data['cid']
            log.info('Loaded data: %s' % self.data)

    def save(self):
        db.instances.update({'id': self.id}, {'$set': self.data}, upsert=True)

    def remove(self):
        self.stop()
        db.instances.remove({'id': self.id})

    def start(self):
        env_id, node_id = self.data['env_id'], self.data['node_id']
        node_path = os.path.join(agent_dir, env_id, node_id)

        templates_path = os.path.join(node_path, 'templates')
        _makedirs(templates_path)

        node_data = db.nodes.find_one({'env_id': env_id, 'node_id': node_id})

        mounts = ['-v', '%s:%s:ro' % (templates_path,
                                      os.path.join(container_dir, 'templates'))]

        if node_data['app_path']:
            mounts += ['-v', '%s:%s:ro' % (node_data['app_path'],
                                           os.path.join(container_dir, 'app'))]

        ports = []
        for port in node_data['ports'].values():
            ports += ['-p', str(port)]

        # TODO: Use API when it can implement port mapping and read-only mounts
        cmd = ['docker', 'run', '-d'] + mounts + ports + [node_data['image']]
        self.data['cid'] = check_output(cmd).strip()
        log.info('Started with cid: %s' % self.data['cid'])

        # Getting ports
        public_ports = {}
        for name, p in node_data['ports'].iteritems():
            public_ports[name] = int(docker_client.port(self.data['cid'], p))

        self.config_set_ports(public_ports)
        self.config_enable()

        self.save()

    def stop(self):
        self.config_disable()
        log.info('Stopping')
        log.info(self.data)
        cid = self.data.get('cid')
        if cid:
            log.info('Stopping cid: %s' % cid)
            docker_client.stop(cid)

    def restart(self):
        self.stop()
        self.start()

    def reload(self):
        code = call(['lxc-attach', '-n', self.data['cid'], '--', '/bin/bash',
                     os.path.join(container_dir, 'files', 'autoload.sh')])
        if code != 0:
            # No user-defined autoload.sh or script wants to reload; restart.
            self.restart()

    def config_set_ports(self, ports):
        instance_key = self.data['instance_key']
        etcd_client.delete('%s/ports' % self.instance_key)
        for name, port in ports.iteritems():
            etcd_client.set('%s/ports/%s' % (instance_key, name), port)

    def config_enable(self):
        instance_key = self.data['instance_key']
        etcd_client.set('%s/enabled' % instance_key, True)

    def config_disable(self):
        instance_key = self.data['instance_key']
        etcd_client.set('%s/enabled' % instance_key, False)


def instance(func):

    def method(instance_id, *args, **kwargs):
        func(Instance(instance_id), *args)

    return method


def _load_deploy(options):
    log.info('Loading deploy from options: %s' % options)

    # Pull image
    if options['sha']:
        # TODO: use image versions from sha
        image = '%s/sys%s/%s' % (options['registry_url'], options['system_id'],
                                 options['node_name'])
    else:
        image = 'stretch_agent/sys%s/%s' % (options['system_id'],
                                            options['node_name'])

    # TODO: "Invalid namespace name (3), only [a-z0-9_] are allowed,
    # size between 4 and 30": enforce all of this for node name
    docker_client.pull(image)

    # Load and compile templates
    context = {'environment': options['env_name']}

    src = os.path.join('salt://templates', options['env_id'],
                       options['node_id'])
    dest = os.path.join(agent_dir, options['env_id'], options['node_id'],
                        'templates')
    _clear_path(dest)

    with _make_temp_dir() as temp_dir:
        __salt__['cp.get_dir'](src, temp_dir)

        for dirpath, dirnames, filenames in os.walk(temp_dir):
            rel_dir = os.path.relpath(dirpath, temp_dir)
            dest_dir = os.path.join(dest, rel_dir)
            loader = jinja2.loaders.FileSystemLoader(dirpath)
            env = jinja2.Environment(loader=loader)
            for filename in filenames:
                dest_file = os.path.splitext(filename)[0]
                data = env.get_template(filename).render(context)
                with open(os.path.join(dest_dir, dest_file), 'w') as f:
                    f.write(data)

    data = {'image': image, 'app_path': options['app_path'],
            'ports': options['node_ports']}
    query = {'env_id': options['env_id'], 'node_id': options['node_id']}
    db.nodes.update(query, {'$set': data}, upsert=True)


@instance
def add_instance(instance, options):
    _load_deploy(options)
    instance.data = {
        'node_id': options['node_id'],
        'env_id': options['env_id'],
        'instance_key': options['instance_key']
    }
    instance.start()


@instance
def remove_instance(instance):
    instance.remove()


@instance
def reload(instance):
    instance.reload()


@instance
def restart(instance):
    instance.restart()


@instance
def deploy(instance, options):
    instance.stop()
    _load_deploy(options)
    instance.data['node_id'] = options['node_id']
    instance.data['env_id'] = options['env_id']
    instance.data['instance_key'] = options['instance_key']
    instance.start()


def main():
    for instance in db.instances.find(fields=['id']):
        Instance(instance['id']).start()


@contextmanager
def _make_temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


def _makedirs(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def _delete_path(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def _clear_path(path):
    _delete_path(path)
    _makedirs(path)


# Until Docker 0.7 (or production-level process monitoring), this hack will
# automatically start containers at system startup for now.
if __name__ == '__main__':
    main()
