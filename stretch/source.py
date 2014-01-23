from threading import Timer
from django.conf import settings

from stretch import utils


class Source(object):
    """
    A base class that provides attributes and methods common to
    multiple source subclasses.
    """

    def __init__(self, options):
        """
        :Parameters:
          - `options`: dictionary containing source options
        """
        self.options = options
        self.path = None
        self.is_live = False

    def clone(self, options={}):
        """
        Pulls and clones the source to a temporary directory.

        Returns (path to the newly-pulled code, {version tag, None}).

        :Parameters:
          - `options`: optional dictionary that specifies what to pull.
        """
        path, tag = self.pull(options)
        return utils.temp_dir(path), tag

    def pull(self, options):
        """
        Returns path to the newly-pulled code.

        :Parameters:
          - `options`: dictionary that specifies what to pull.
        """
        raise NotImplementedError  # pragma: no cover

    def get_option(self, name):
        """
        Returns the option with `name` and returns None if not found.

        :Parameters:
          - `name`: the option's name
        """
        return self.options.get(name, None)

    def require_option(self, name):
        """
        Returns the option with `name` and fails if not found.

        :Parameters:
          - `name`: the option's name
        """
        option = self.options.get(name, None)
        if not option:
            raise NameError('no option "%s" defined' % name)
        return option


class LiveSource(Source):
    """
    A source that triggers a callback when its files are changed.
    """

    def __init__(self, options):
        """
        :Parameters:
          - `options`: dictionary containing source options. The
            `live` option determines if the source should automatically
            reload when relevant files change.
        """
        super(LiveSource, self).__init__(options)
        self.is_live = self.options.get('live', True)
        self.system_name = None
        self.path_buffer_flush = self.options.get('flush', 0.2)

        self._path_buffer = []
        self._timer = None

    def start_watch(self):
        if self.is_live:
            self.watch()

    def watch(self):
        raise NotImplementedError

    def on_file_change(self, path):
        self._path_buffer.append(path)
        if self._timer:
            self._timer.cancel()
        self._timer = Timer(self.path_buffer_flush, self._push_buffer)
        self._timer.start()

    def _push_buffer(self):
        self._on_files_change(self._path_buffer)
        self._path_buffer = []

    def _on_files_change(self, paths):
        pass
        '''
        # Reload nodes only if an event took place within the node's
        # monitored paths.
        snapshot = parser.Snapshot(self.pull())
        autoload_nodes = []

        for node, paths in snapshot.monitored_paths.iteritems():
            for event in events:
                path = event.src_path

                if hasattr(event, 'dest_path'):
                    path = event.dest_path

                if any([utils.path_contains(mpath, path) for mpath in paths]):
                    autoload_nodes.append(node)
                    break

        if autoload_nodes:
            signals.sync_source.send(sender=self, nodes=autoload_nodes, system_name=self.system.name)
        '''


class NoSourceException(Exception):  # pragma: no cover
    """Raised if a system does not have an assigned source."""
    def __str__(self):
        return ('No source was defined for system. Add a source for the '
                'system in settings.py')


class UndefinedSourceException(Exception):  # pragma: no cover
    """Raised if a system tries to use a source that does not exist."""
    pass


def get_sources(system):
    source_map = get_source_map(settings.STRETCH_SOURCES)
    return source_map.get(system.name, [])


def watch():
    source_map = get_source_map(settings.STRETCH_SOURCES)
    for system_name, sources in source_map.iteritems():
        [source.start_watch() for source in sources if source.is_live]


@utils.memoized
def get_source_classes():
    from stretch import sources as stretch_sources
    return utils.find_subclasses(stretch_sources, Source)


def get_source_class(name):
    for source_class in get_source_classes():
        if source_class.name == name:
            return source_class
    raise UndefinedSourceException('Source "%s" does not exist.' % name)


@utils.memoized
def get_source_map(sources):
    source_map = {}

    for system_name, system_sources in sources.iteritems():
        source_map[system_name] = []

        for source in system_sources:
            options = source.get('options', {})
            source_class = get_source_class(source.get('source'))
            source_obj = source_class(options)
            source_obj.system_name = system_name
            source_map[system_name].append(source_obj)

    return source_map
