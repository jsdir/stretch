import os
import errno
import docker
import pymongo
import shutil
import tempfile
import contextlib
import jinja2
from subprocess import call, check_output


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
            self.data = data

    def save(self):
        db.instances.update({'id': self.id}, {'$set': self.data}, upsert=True)

    def remove(self):
        self.stop()
        db.instances.remove({'id': self.id})

    def start(self):
        env_id, node_id = self.data['env_id'], self.data['node_id']
        node_path = os.path.join(agent_dir, env_id, node_id)
        config_path = os.path.join(node_path, 'config.json')
        makedirs(os.path.join(node_path, 'templates'))
        if not os.path.exists(config_path):
            with open(config_path) as f:
                f.write('{}')

        node_data = db.nodes.find_one({'env_id': env_id, 'node_id':node_id})

        mounts = ['-v', '%s:%s:ro' % (node_path, container_dir)]
        if node_data['app_path']:
            mounts += ['-v', '%s:%s:ro' % (node_data['app_path'],
                                           os.path.join(container_dir, 'app'))]
        ports = []
        for port in node_data['ports']:
            ports += ['p', '%s:%s' % (port, port)]

        # TODO: Use API when it can implement port mapping and read-only mounts
        self.data['cid'] = check_output((['docker', 'run', '-d'] + mounts +
                                         ports + [node_data['image']])).strip()
        self.save()

    def stop(self):
        docker_client.stop(self.data['cid'])

    def restart(self):
        self.stop()
        self.start()

    def reload(self):
        code = call(['lxc-attach', '-n', self.cid, '--', '/bin/bash',
                     os.path.join(container_dir, 'autoload.sh')])
        if code != 0:
            # No user-defined autoload.sh or script wants to reload; restart.
            self.restart()


def instance(func):

    def method(instance_id, *args, **kwargs):
        func(Instance(instance_id), *args, **kwargs)

    return method


def load_config(env_id, node_configs):
    env_dir = os.path.join(agent_dir, env_id)
    for node_id, config in node_configs.iteritems():
        with open(os.path.join(env_dir, node_id, 'config.json'), 'w') as f:
            f.write(config)


@instance
def add_instance(instance, node_id, env_id):
    instance.data = {'node_id': node_id, 'env_id': env_id}
    instance.start()


@instance
def remove_instance(instance):
    instance.remove()


@contextlib.contextmanager
def make_temp_dir():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@instance
def deploy(instance, env, node, ports, registry_url, sha=None, app_path=None):
    # TODO: make ports multidimensional
    if not sha and not app_path:
        raise Exception('either release sha or app path must be specified')

    # Pull image
    if sha:
        image = '%s/%s/%s#%s' % (registry_url, env['id'], node['name'], sha)
    else:
        image = '%s/stretch-agent/%s/%s' % (registry_url, env['id'],
                                            node['name'])
    docker.pull(image)

    data = {'image': image, 'app_path': app_path, 'ports': ports}
    query = {'env_id': env['id'], 'node_id': node['id']}
    db.nodes.update(query, {'$set': data}, upsert=True)

    instance.stop()

    # Load and compile templates
    context = {'environment': env['name']}

    src = os.path.join('salt://templates', env['id'], node['id'])
    dest = os.path.join(agent_dir, env['id'], node['id'], 'templates')
    clear_path(dest)

    with make_temp_dir() as temp_dir:
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


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def delete_path(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def clear_path(path):
    delete_path(path)
    makedirs(path)


current_module = __import__(__name__)
for name in ('start', 'stop', 'reload', 'restart'):

    @instance
    def func(instance):
        getattr(instance, name)()

    setattr(current_module, name, func)
