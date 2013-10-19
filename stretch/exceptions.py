import os


class UndefinedSource(Exception):
    """Raised if a system tries to use a source that does not exist."""
    def __str__(self):
        return 'No source defined. Add sources for the system in settings.py'


class UndefinedBackend(Exception):
    """Raised if an environment tries to use a backend that does not exist."""
    def __str__(self):
        return ('No backend defined. Add backends for the environment in '
                'settings.py')


class MissingFile(Exception):
    """Raised if a Snapshot cannot find a necessary file."""
    def __init__(self, expected):
        file_name = os.path.split(expected)[1]
        super(MissingFile, self).__init__('%s does not exist, (expected %s)' %
                                          (file_name, expected))


class UndefinedParam(Exception):
    """Raised if a Snapshot cannot find a necessary parameter within a file."""
    def __init__(self, param, file_name):
        super(UndefinedParam, self).__init__('param "%s" does not exist in %s'
                                             % (param, file_name))
