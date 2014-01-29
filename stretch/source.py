from stretch import config, utils
from stretch.extension import Extension


class Source(Extension):
    """
    A base class that provides attributes and methods common to
    multiple source subclasses.
    """

    name = 'source'
    config_section = 'sources'
    is_live = False

    def __init__(self, options):
        super(Source, self).__init__(options)
        self.path = None

    def pull(self, options):
        """
        Returns path to the newly-pulled code.

        :Parameters:
          - `options`: options about what to pull.
        """
        utils.merge(self.options, options)


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


class SourceException(Exception): pass


def get_source_by_name(source_name):
    for source, data in config['sources'].iteritems():
        if source_name == source:
            source_type = data.get('type')

            if not source_type:
                raise SourceException('"type" undefined for source "%s"'
                                      % source)

            # Attempt to load the source type.
            return get_source_class(source_type)(data.get('options', {}))

    # Raise an exception if the source was not found.
    raise SourceException('could not find source "%s" in config.yml'
                          % source_name)


def get_source_classes():
    from stretch import sources
    return utils.find_subclasses(sources, Source)


def get_source_class(source_type):
    for source_class in get_source_classes():
        if source_class.name == source_type:
            return source_class
    raise SourceException('source with type "%s" does not exist' % source_type)
