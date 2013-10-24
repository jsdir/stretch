import os
import errno
import json
import docker
import pymongo
import shutil
import tempfile
from contextlib import contextmanager
import jinja2
from subprocess import call, check_output
import logging
log = logging.getLogger(__name__)
docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.4')
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

        config_path = os.path.join(node_path, 'config')
        app_path = os.path.join(node_path, 'app')
        files_path = os.path.join(node_path, 'files')
        templates_path = os.path.join(node_path, 'templates')

        _makedirs(config_path)
        _makedirs(app_path)
        _makedirs(files_path)
        _makedirs(templates_path)

        if not os.path.exists(os.path.join(config_path, 'config.json')):
            with open(os.path.join(config_path, 'config.json'), 'w') as f:
                f.write('{}')

        node_data = db.nodes.find_one({'env_id': env_id, 'node_id': node_id})

        mounts = ['-v', '%s:%s:ro' % (config_path,
                                      os.path.join(container_dir, 'config'))]
        mounts += ['-v', '%s:%s:ro' % (templates_path,
                                      os.path.join(container_dir, 'templates'))]

        if node_data['app_path']:
            mounts += ['-v', '%s:%s:ro' % (node_data['app_path'],
                                           os.path.join(container_dir, 'app'))]

        ports = []
        for port in node_data['ports']:
            ports += ['-p', '%s:%s' % (port, port)]

        # TODO: Use API when it can implement port mapping and read-only mounts
        # TODO: Use alternative of check_output for python 2.6
        self.data['cid'] = check_output((['docker', 'run', '-d'] + mounts +
                                         ports + [node_data['image']])).strip()
        log.info('Starting cid: %s' % self.data['cid'])
        self.save()

    def stop(self):
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
        code = call(['lxc-attach', '-n', self.cid, '--', '/bin/bash',
                     os.path.join(container_dir, 'files', 'autoload.sh')])
        if code != 0:
            # No user-defined autoload.sh or script wants to reload; restart.
            self.restart()


def instance(func):

    def method(instance_id, *args, **kwargs):
        func(Instance(instance_id), *args) #, **kwargs)

    return method


def load_config(env_id, node_configs):
    env_dir = os.path.join(agent_dir, str(env_id))
    for node_id, config in node_configs.iteritems():
        config_path = os.path.join(env_dir, node_id, 'config')
        _makedirs(config_path)
        with open(os.path.join(config_path, 'config.json'), 'w') as f:
            json.dump(config, f)


@instance
def add_instance(instance, node_id, env_id):
    instance.data = {'node_id': str(node_id), 'env_id': str(env_id)}
    instance.start()


@instance
def remove_instance(instance):
    instance.remove()


@instance
def start(instance):
    instance.start()


@instance
def stop(instance):
    instance.stop()


@instance
def reload(instance):
    instance.reload()


@instance
def restart(instance):
    instance.restart()


@contextmanager
def _make_temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@instance
def deploy(instance, system_id, env, node, ports, registry_url, sha=None,
           app_path=None):
    # TODO: Find solution for parameter type problems
    if sha == 'None':
        sha = None
    if app_path == 'None':
        app_path = None

    # TODO: make ports multidimensional
    if not sha and not app_path:
        raise Exception('either release sha or app path must be specified')

    # Pull image
    if sha:
        image = '%s/sys%s/%s' % (registry_url, system_id, node['name'])
    else:
        image = 'stretch_agent/sys%s/%s' % (system_id, node['name'])

    # TODO: "Invalid namespace name (3), only [a-z0-9_] are allowed,
    # size between 4 and 30": enforce all of this for node name
    docker_client.pull(image)

    data = {'image': image, 'app_path': app_path, 'ports': ports}
    query = {'env_id': env['id'], 'node_id': node['id']}
    db.nodes.update(query, {'$set': data}, upsert=True)

    instance.data['env_id'] = env['id']
    instance.data['node_id'] = node['id']
    instance.stop()

    # Load and compile templates
    context = {'environment': env['name']}

    src = os.path.join('salt://templates', env['id'], node['id'])
    dest = os.path.join(agent_dir, env['id'], node['id'], 'templates')
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

    instance.start()


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
    for instance in db.instances.find(fields=['id']):
        Instance(instance['id']).start()
