import os
import re
import copy
import yaml
import docker
import tarfile
import logging
from contextlib import contextmanager

from stretch import utils

log = logging.getLogger(__name__)
docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.6', timeout=10)


class Snapshot(object):

    def __init__(self, path):
        self.path = path
        self.nodes = []
        self.config = {}
        self.parse()

    @classmethod
    @contextmanager
    def create_from(cls, path):
        yield cls(path)
        utils.delete_dir(snapshot_dir)

    @classmethod
    @contextmanager
    def create_from_archive(cls, path):
        snapshot_dir = utils.temp_dir()
        tar_file = tarfile.open(path)
        tar_file.extractall(snapshot_dir)
        tar_file.close()
        yield cls(snapshot_dir)
        utils.delete_dir(snapshot_dir)

    def parse(self):
        log.info('Parsing "%s"...' % self.path)

        # Get the build files from the root of the source
        build_files = get_build_files(self.path, ['stretch.yml'])

        # Get global config
        config_path = build_files.get('config.yml')
        if config_path:
            self.config = get_data(config_path)

        # Determine the node declaration from the root build files
        stretch_file = build_files['stretch.yml']
        self.stretch_data = get_data(stretch_file)
        nodes = self.stretch_data.get('nodes')

        if nodes:
            # Mulitple node declaration used
            self.multiple_nodes = True
            self.build_files = build_files

            for name, path in nodes.iteritems():
                node_path = os.path.join(self.path, path)
                self.nodes.append(Node(node_path, self, name))

        else:
            # Individual node declaration used
            self.multiple_nodes = False
            name = self.stretch_data.get('name')
            if name:
                self.nodes.append(Node(self.path, self, name))
            else:
                raise UndefinedParamException('name', stretch_file)

    def archive(self, release):
        # Archive the release
        utils.make_dir(os.path.dirname(release.archive_path))

        # Tar snapshot buffer
        tar_file = tarfile.open(release.archive_path, 'w:gz')
        tar_file.add(self.path, '/')
        tar_file.close()

        # Delete snapshot buffer
        self.clean_up()

    def build(self, release):
        # TODO: Run multiple builds simultaneously

        self.run_task('before_build', release)

        containers = dict([
            (node.name, node.container.build(release)) for node in self.nodes
        ])


        '''
        for image in images:
            log.info('Pushing "%s" to registry...')

            image = ':'.join(image.split(':')[0:-1])
            for line in docker_client().push(image, stream=True):
                # Log the push process
                log.info(line)

            log.info('Push complete.')
        '''

        self.run_task('after_build', release)
        return containers

    def run_task(self, task, release):
        run_task(self, task, release)
        [run_task(node, task, release) for node in self.nodes]

    def clean_up(self):
        utils.delete_dir(self.path)


class Node(object):

    def __init__(self, path, snapshot, name):
        self.path = path
        self.name = name
        self.snapshot = snapshot
        self.config = copy.deepcopy(snapshot.config)
        self.templates_path = os.path.join(self.path, 'templates')
        self.stretch_data = {}

        # Begin parsing node
        self.parse()

    def parse(self):
        log.info('Parsing node (%s) at "%s"' % (self.name, self.path))

        # Get the build files from the root of the node
        build_files = get_build_files(self.path)

        # Get template path
        stretch_path = build_files.get('stretch.yml')
        if stretch_path:
            self.stretch_data = get_data(stretch_path)
            templates_path = self.stretch_data.get('templates')
            if templates_path:
                self.templates_path = os.path.join(self.path, templates_path)

        # Get global config
        config_path = build_files.get('config.yml')
        if config_path:
            utils.merge(self.config, get_data(config_path))

        # Get container
        self.container = Container(self.path, [], self)


class Container(object):

    def __init__(self, path, child_paths, node):
        self.path = path
        self.container = None
        self.node = node

        # Check for cyclic dependencies
        if self.path in child_paths:
            raise CyclicDependencyException(child_paths)

        # Check for Dockerfile
        self.dockerfile = os.path.join(self.path, 'Dockerfile')
        if os.path.exists(self.dockerfile):
            log.info('Found container in "%s"' % path)
        else:
            raise MissingFileException(self.dockerfile)

        # Get base image from container.yml if it exists
        base_container = None
        container_spec_path = os.path.join(self.path, 'container.yml')
        if os.path.exists(container_spec_path):
            path = get_data(container_spec_path).get('from')
            log.info('Container requires "%s"' % path)
            base_container = os.path.normpath(os.path.join(self.path, path))

            if base_container:
                child_paths.append(self.path)
                self.container = Container(base_container, child_paths, None)

    def build(self, release):
        client = docker_client()

        if self.container:
            image = self.container.build(release)
            data = open(self.dockerfile).read()
            with open(self.dockerfile, 'w') as dockerfile:
                dockerfile.write('FROM %s\n%s' % (image, data))

        if self.node:
            log.info('Building node "%s"...' % self.node.name)
        else:
            log.info('Building container at "%s"...' % self.path)

        output = ''
        for line in client.build(self.path, rm=True, stream=True):
            # Log the build process
            log.debug(line)
            output += line

        # Check if the image was built successfully
        match = re.search(r'Successfully built ([0-9a-f]+)', output)
        if not match:
            raise BuildException(
                'Failed to build image from "%s".' % self.dockerfile
            )

        image = match.group(1)

        log.info(' - container id: %s' % image)
        return image


class MissingFileException(Exception): pass # pragma: no cover


class BuildException(Exception): pass # pragma: no cover


class CyclicDependencyException(Exception):  # pragma: no cover
    """Raised when an image depends on its ancestor."""
    def __init__(self, child_paths):
        super(CyclicDependencyException, self).__init__(
            'Attempted to link the containers but encountered a cyclic '
            'dependency. (%s)' % child_paths
        )


class UndefinedParamException(Exception):  # pragma: no cover
    """Raised if a necessary parameter cannot be found within a file."""
    def __init__(self, param, file_name):
        super(UndefinedParamException, self).__init__(
            'param "%s" does not exist in "%s"' % (param, file_name)
        )


def run_task(obj, task, release):
    if task in (
        'before_build', 'after_build',
        'before_deploy', 'after_deploy',
        'before_rollback', 'after_rollback'
    ):
        command = obj.stretch_data.get(task)
        if command:
            log.info('Executing "%s" task in "%s"...' % (task, obj.path))
            log.info(' - %s' % command)
            execute_command(command, release, obj.path)
            log.info('Finished executing "%s" task.' % task)


def execute_command(command, release, path):
    env = os.environ.copy()
    env['STRETCH_RELEASE_ID'] = release.release_id
    env['STRETCH_RELEASE_NAME'] = release.name

    cmd = 'cd %s && %s' % (path, command)
    utils.run(cmd, env=env, shell=True)


def get_build_files(path, required_files=[]):
    """
    Return all build files in a path.
    """
    build_files = {}

    for file_name in ('stretch.yml', 'config.yml'):
        file_path = os.path.join(path, file_name)
        if os.path.exists(file_path):
            log.info('Found %s at "%s"' % (file_name, file_path))
            build_files[file_name] = file_path
        elif file_name in required_files:
            raise MissingFileException(file_path)

    return build_files


def get_data(path):
    return yaml.load(open(path).read()) or {}


#@utils.memoized
def docker_client():
    return docker.Client(base_url='unix://var/run/docker.sock',
                         version='1.6', timeout=60)
