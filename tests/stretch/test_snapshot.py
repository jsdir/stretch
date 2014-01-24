import functools
from mock import Mock, patch, call
from nose.tools import raises
from django.test import TestCase

from stretch import snapshot, testutils


def mock_fs(func, root='/'):

    @functools.wraps(func)
    def wrapper(self, *args, **kwds):
        fs = testutils.MockFileSystem(root)
        with patch('stretch.snapshot.os.path.exists', fs.exists):
            with patch('stretch.snapshot.open', fs.open, create=True):
                return func(self, fs, *args, **kwds)

    return wrapper


class TestSnapshot(TestCase):

    @mock_fs
    def test_requires_root_stretch(self, fs):
        with self.assertRaises(snapshot.MissingFileException):
            snap = snapshot.Snapshot('/')

    @mock_fs
    def test_config(self, fs):
        fs.add_file('stretch.yml', 'nodes:\n  node: node')
        fs.add_file('config.yml', 'root_config:\n  root_key: root\n  k: 1')
        fs.add_file('node/Dockerfile')
        fs.add_file('node/config.yml',
            'root_config:\n  k: 2\nnode_config:\n  node_key: node')

        snap = snapshot.Snapshot('/')
        node = snap.nodes[0]

        self.assertEquals(snap.config['root_config'], {
            'root_key': 'root', 'k': 1
        })

        self.assertEquals(node.config['root_config']['root_key'], 'root')
        self.assertEquals(node.config['root_config']['k'], 2)
        self.assertEquals(node.config['node_config']['node_key'], 'node')

    @mock_fs
    def test_dockerfiles_required(self, fs):
        # Single-node spec
        fs.add_file('stretch.yml', 'name: node_name')
        with self.assertRaises(snapshot.MissingFileException):
            snap = snapshot.Snapshot('/')

        # Multi-node spec
        fs.add_file('stretch.yml', 'nodes:\n  node: node')
        fs.add_file('node/stretch.yml')
        with self.assertRaises(snapshot.MissingFileException):
            snap = snapshot.Snapshot('/')

    @mock_fs
    def test_cyclic_dependency_throws_error(self, fs):
        fs.add_file('stretch.yml', 'name: node_name')
        fs.add_file('Dockerfile')
        fs.add_file('container.yml', 'from: .')

        with self.assertRaises(snapshot.CyclicDependencyException):
            snap = snapshot.Snapshot('/')

        fs.add_file('container.yml', 'from: base/image')
        fs.add_file('base/image/Dockerfile')
        fs.add_file('base/image/container.yml', 'from: ../..')

        with self.assertRaises(snapshot.CyclicDependencyException):
            snap = snapshot.Snapshot('/')

    @mock_fs
    def test_single_node_name(self, fs):
        fs.add_file('stretch.yml')
        fs.add_file('Dockerfile')

        with self.assertRaises(snapshot.UndefinedParamException):
            snap = snapshot.Snapshot('/')

        fs.add_file('stretch.yml', 'name: node_name')
        snap = snapshot.Snapshot('/')

        node = snap.nodes[0]
        self.assertEquals(node.name, 'node_name')

    @mock_fs
    def test_templates_single_node(self, fs):
        fs.add_file('stretch.yml', 'name: node_name')
        fs.add_file('Dockerfile')
        snap = snapshot.Snapshot('/')
        node = snap.nodes[0]

        self.assertEquals(node.templates_path, '/templates')

        fs.add_file('stretch.yml', 'name: node_name\ntemplates: foo/bar')
        snap = snapshot.Snapshot('/')
        node = snap.nodes[0]

        self.assertEquals(node.templates_path, '/foo/bar')

    @mock_fs
    def test_templates_multi_node(self, fs):
        fs.add_file('stretch.yml', 'nodes:\n  node: node')
        fs.add_file('node/Dockerfile')
        snap = snapshot.Snapshot('/')
        node = snap.nodes[0]

        self.assertEquals(node.templates_path, '/node/templates')

        fs.add_file('node/stretch.yml', 'templates: foo/bar')
        snap = snapshot.Snapshot('/')
        node = snap.nodes[0]

        self.assertEquals(node.templates_path, '/node/foo/bar')

    @patch('stretch.snapshot.Snapshot.run_task')
    @patch('stretch.snapshot.docker_client')
    @mock_fs
    def test_build(self, fs, docker_client, run_task):
        fs.add_file('stretch.yml',
            'before_build: "b"\n\nnodes:\n  node1: node1\n  node2: node2')
        fs.add_file('node1/Dockerfile', 'source')
        fs.add_file('node1/container.yml', 'from: ../base/image')
        fs.add_file('node2/Dockerfile', 'source')
        fs.add_file('node2/container.yml', 'from: ../base/image')
        fs.add_file('node2/stretch.yml', 'after_build: "a"')
        fs.add_file('base/image/Dockerfile', 'source')

        client = Mock()
        client.build.return_value = ['logs', 'Successfully built abc123']
        client.push.return_value = []
        docker_client.return_value = client

        release = Mock()
        release.pk = 4

        with testutils.patch_settings(STRETCH_REGISTRY='reg'):
            snap = snapshot.Snapshot('/')
            snap.build(release, {'node1': 1, 'node2': 2})

        run_task.assert_has_calls([
            call('before_build', release),
            call('after_build', release)
        ])

        self.assertEquals(fs.open('/node1/Dockerfile').read(),
            'FROM abc123\nsource'
        )
        self.assertEquals(fs.open('/node2/Dockerfile').read(),
            'FROM abc123\nsource'
        )
        self.assertEquals(fs.open('/base/image/Dockerfile').read(), 'source')
