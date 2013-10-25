import os
from mock import Mock


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

    def read_file(self, path):
        data = self.files.get(path)
        if data == None:
            raise IOError('file (%s) not found' % path)
        return data


def mock_attr(**kwargs):
    mock = Mock()
    for key, value in kwargs.iteritems():
        setattr(mock, key, value)
    return mock
