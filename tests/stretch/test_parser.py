from mock import patch
from nose.tools import eq_, raises, assert_raises
from contextlib import contextmanager
from unittest import TestCase

from stretch import parser, exceptions, testutils


class TestParser(TestCase):
    def setUp(self):
        pass

    @contextmanager
    def mock_fs(self, root):
        mock_fs = testutils.MockFileSystem(root)
        with patch('stretch.parser.os.path.exists', mock_fs.exists):
            with patch('stretch.parser.open', mock_fs.open, create=True):
                yield mock_fs

    @raises(exceptions.MissingFile)
    def test_require_root_stretch(self):
        with self.mock_fs('/foo') as fs:
            fs.set_files({})
            parser.Snapshot('/foo')

    @patch('stretch.parser.Container')
    def test_individual_declaration(self, container):
        with self.mock_fs('/foo') as fs:
            fs.set_files({'stretch.yml': ''})
            with assert_raises(exceptions.UndefinedParam):
                snapshot = parser.Snapshot('/foo')

            fs.set_files({'stretch.yml': 'name: foo', 'app': {}})
            container.create().path = '/foo'
            snapshot = parser.Snapshot('/foo')
            monitored_paths = snapshot.get_monitored_paths()
            eq_(monitored_paths.items()[0][0].name, 'foo')
            eq_(monitored_paths.items()[0][1], ['/foo/app'])

    def test_get_plugins(self):
        with self.mock_fs('/foo') as fs:
            fs.set_files({'stretch.yml': ''})


class TestNode(object):
    pass


class TestContainer(object):
    pass
