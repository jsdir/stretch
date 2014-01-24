import functools
from mock import patch
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
        # TODO: "/stretch.yml"
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
        # TODO: Dockerfile
        with self.assertRaises(snapshot.MissingFileException):
            snap = snapshot.Snapshot('/')

        # Multi-node spec
        fs.add_file('stretch.yml', 'nodes:\n  node: node')
        fs.add_file('node/stretch.yml')
        # TODO: Dockerfile
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

    @mock_fs
    def test_build(self, fs):
        """
        fs.add_file('base')
        fs.add_file('node1')
        fs.add_file('node2')

        build()
        #assert command called with before_build in correct dir

        # then

        build.calls[0] == call(base)
        #assert build.calls[1] == call(node2) and build.calls[2] = call(node1) or
        #build.calls[1] = call(node1) and build.calls[2] = call(node2)

        fs.add_file('base')
        fs.add_file('base < node1')
        fs.add_file('base < node1 < node2')

        build.assert_has_calls([call(base, 'dockerfilecontent'), call(node1), call(node2)])

        # then

        #assert command called with before_deploy in correct dir
        """
