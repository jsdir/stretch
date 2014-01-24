import os
import re
import copy
import yaml
import docker
import tarfile
import logging
from django.conf import settings

from stretch import utils


log = logging.getLogger(__name__)
docker_client = docker.Client(base_url='unix://var/run/docker.sock',
                              version='1.6', timeout=10)


class Snapshot(object):

    def __init__(self, path):
        self.path = path
        self.nodes = []
        self.config = {}
        #self.containers = []
        self.parse()

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

        # Build images
        self.build(release)
        snapshot.build_and_push(release)

        # Delete snapshot buffer
        self.clean_up()

    def build(self, release, node_map):
        # TODO: Run multiple builds simultaneously

        self.run_task('before_build', release)

        images = [n.container.build(release, node_map) for n in self.nodes]
        for image in images:
            log.info('Pushing "%s" to registry...')

            for line in docker_client().push(image, stream=True):
                # Log the push process
                log.info(line)

            log.info('Push complete.')

        self.run_task('after_build', release)

    def run_task(self, task, release):
        [node.run_task(task, release) for node in self.nodes]

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

    def run_task(self, task, release):
        if task in (
            'before_build', 'after_build',
            'before_deploy', 'after_deploy',
            'before_rollback', 'after_rollback'
        ):
            command = self.stretch_data.get(task)
            if command:
                log.info('Executing "%s" task in "%s"...' % (task, self.path))
                self.execute_command(command, release)
                log.info('Finished executing "%s" task.' % task)

    def execute_command(self, command, release):
        env = os.environ.copy()
        env['STRETCH_RELEASE_ID'] = str(release.pk)
        env['STRETCH_RELEASE_TAG'] = release.tag
        env['STRETCH_RELEASE_NAME'] = release.name
        env['STRETCH_STASH_PATH'] = release.system.stash_path

        cmd = 'cd %s && %s' % (self.path, command)
        utils.run(cmd, env=env, shell=True)


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

    def build(self, release, node_map):
        client = docker_client()

        if self.container:
            image = self.container.build(release, node_map)
            data = open(self.dockerfile).read()
            with open(self.dockerfile, 'w') as dockerfile:
                dockerfile.write('FROM %s\n%s' % (image, data))

        tag = None
        if self.node:
            registry = settings.STRETCH_REGISTRY
            tag = '%s/stretch/builds/%s:%s' % (
                registry, node_map[self.node.name], release.pk
            )
            log.info('Building node "%s" as "%s"' % (self.node.name, tag))
        else:
            log.info('Building container at "%s"...' % self.path)

        for line in client.build(self.path, tag=tag, rm=True, stream=True):
            # Log the build process
            log.info(line)

        # Check if the image was built successfully
        match = re.search(r'Successfully built ([0-9a-f]+)', line)
        if not match:
            raise BuildException(
                'Failed to build image from "%s".' % self.dockerfile
            )

        if self.node:
            image = tag
        else:
            image = match.group(1)

        log.info(' - Image tagged as "%s"' % image)
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


@utils.memoized
def docker_client():
    return docker.Client(base_url='unix://var/run/docker.sock',
                         version='1.6', timeout=10)
