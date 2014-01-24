import os
from mock import MagicMock, patch
from django.conf import settings


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
            self.add_file(key, value, add_to_map=False)

    def add_file(self, path, data='', add_to_map=True):
        self.files[os.path.join(self.root, path)] = data
        if add_to_map:
            directory = self.file_map
            comps = path.split(os.sep)
            for comp in comps[0:-1]:
                if comp in directory:
                    directory = directory[comp]
                else:
                    directory[comp] = {}
                    directory = directory[comp]
            directory[comps[-1]] = data

    def exists(self, path):
        return path in self.files.keys()

    def open(self, path, mode='r'):
        handle = MagicMock(spec=file)

        def write(data):
            self.add_file(path, data)

        handle.write = write
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


class patch_settings(object):

    def __init__(self, **kwargs):
        super(patch_settings, self).__init__()
        self.marker = object()
        self.old_settings = {}
        self.kwargs = kwargs

    def start(self):
        for setting, new_value in self.kwargs.items():
            old_value = getattr(settings, setting, self.marker)
            self.old_settings[setting] = old_value
            setattr(settings, setting, new_value)

    def stop(self):
        for setting, old_value in self.old_settings.items():
            if old_value is self.marker:
                delattr(settings, setting)
            else:
                setattr(settings, setting, old_value)

    def __enter__(self):
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
