from mock import patch
from nose.tools import eq_, raises, assert_raises
from contextlib import contextmanager

from stretch import parser, exceptions, testutils


class TestParser(object):
    @contextmanager
    def mock_fs(self, root):
        mock_fs = testutils.MockFileSystem(root)
        with patch('os.path.exists', mock_fs.exists):
            with patch('stretch.parser.read_file', mock_fs.read_file):
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

    def test_container(self):
        pass
