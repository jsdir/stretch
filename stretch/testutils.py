import os
import mongomock
from cStringIO import StringIO
from mock import Mock, MagicMock
from flask.ext.testing import TestCase

from stretch.agent import resources, app


class MockFileSystem(object):
    def __init__(self, root):
        self.root = root
        self.files = {}
        self.file_map = {}

    def set_files(self, files):

        def flatten_dict(d):

            def items():
                for key, value in d.items():
                    if isinstance(value, dict):
                        yield key, None
                        for subkey, subvalue in flatten_dict(value).items():
                            yield os.path.join(key, subkey), subvalue
                    else:
                        yield key, value

            return dict(items())

        self.files = {}
        self.file_map = files
        for key, value in flatten_dict(files).iteritems():
            self.files[os.path.join(self.root, key)] = value

    def exists(self, path):
        return path in self.files.keys()

    def open(self, path):
        handle = MagicMock(spec=file)
        handle.write.return_value = None
        handle.__enter__.return_value = handle

        data = self.files.get(path)
        if data == None:
            raise IOError('file (%s) not found' % path)

        handle.read.return_value = data
        return handle

    def walk(self, path):
        rel_path = os.path.relpath(path, self.root)
        if rel_path.startswith('..'):
            return
            yield
        elif rel_path.startswith('.'):
            for t in self.iter_walk(self.root, self.file_map):
                yield t
        else:
            files = self.file_map
            for l in rel_path.split('/'):
                if l in files:
                    files = files[l]
                else:
                    return
                    yield
            for t in self.iter_walk(os.path.join(self.root, rel_path), files):
                yield t

    def iter_walk(self, path, contents):
        dirnames, filenames = [], []
        for key, value in contents.iteritems():
            if isinstance(value, dict):
                dirnames.append(key)
                for t in self.iter_walk(os.path.join(path, key), value):
                    yield t
            else:
                filenames.append(key)
        yield (path, dirnames, filenames)


class AgentTestCase(TestCase):
    def setUp(self):
        self.db = resources.db = mongomock.Connection().db

    def create_app(self):
        app.app.config['TESTING'] = True
        return app.app


def mock_attr(**kwargs):
    mock = Mock()
    for key, value in kwargs.iteritems():
        setattr(mock, key, value)
    return mock


def check_items_equal(l1, l2):
    return len(l1) == len(l2) and sorted(l2) == sorted(l2)


def patch_settings(key, value):
    return patch('django.conf.settings.%s' % key, value)
