import os
import yaml
from mock import Mock, patch
from nose.tools import eq_, raises, assert_raises
from contextlib import contextmanager

from stretch import parser, exceptions


class MockFileSystem(object):
    def __init__(self, root):
        self.root = root
        self.files = {}

    def set_files(self, files):

        def flatten_dict(d):

            def items():
                for key, value in d.items():
                    if isinstance(value, dict) and value:
                        for subkey, subvalue in flatten_dict(value).items():
                            yield os.path.join(key, subkey), subvalue
                    elif isinstance(value, dict):
                        yield key, None
                    else:
                        yield key, value

            return dict(items())

        self.files = {}
        for key, value in flatten_dict(files).iteritems():
            self.files[os.path.join(self.root, key)] = value

    def exists(self, path):
        return path in self.files.keys()

    def read_file(self, path):
        data = self.files.get(path)
        if data == None:
            raise IOError('file (%s) not found' % path)
        return data

    @contextmanager
    def patch(self):
        with patch('os.path.exists', self.exists):
            with patch('stretch.parser.read_file', self.read_file):
                yield


class TestParser(object):
    @raises(exceptions.MissingFile)
    def test_require_root_stretch(self):
        fs = MockFileSystem('/foo')
        fs.set_files({})
        with fs.patch():
            snapshot = parser.Snapshot('/foo')

    @patch('stretch.parser.Container')
    def test_individual_declaration(self, container):
        fs = MockFileSystem('/foo')

        fs.set_files({'stretch.yml': ''})
        with assert_raises(exceptions.UndefinedParam):
            with fs.patch():
                snapshot = parser.Snapshot('/foo')

        fs.set_files({'stretch.yml': 'name: foo', 'app': {}})
        container.create().path = '/foo'
        with fs.patch():
            snapshot = parser.Snapshot('/foo')
            monitored_paths = snapshot.get_monitored_paths()
            eq_(monitored_paths.items()[0][0].name, 'foo')
            eq_(monitored_paths.items()[0][1], ['/foo/app'])

    def test_container(self):
        pass
