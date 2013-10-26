import os
from cStringIO import StringIO
from mock import Mock, MagicMock


class MockFileSystem(object):
    def __init__(self, root):
        self.root = root
        self.files = {}

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
        for key, value in flatten_dict(files).iteritems():
            self.files[os.path.join(self.root, key)] = value

    def exists(self, path):
        return path in self.files.keys()

    def open(self, path):
        print path
        handle = MagicMock(spec=file)
        handle.write.return_value = None
        handle.__enter__.return_value = handle

        data = self.files.get(path)
        if data == None:
            raise IOError('file (%s) not found' % path)

        handle.read.return_value = data
        return handle


def mock_attr(**kwargs):
    mock = Mock()
    for key, value in kwargs.iteritems():
        setattr(mock, key, value)
    return mock


def check_items_equal(l1, l2):
    return len(l1) == len(l2) and sorted(l2) == sorted(l2)
