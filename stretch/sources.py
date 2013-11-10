import os
import git
import hashlib
import logging
import threading
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from django.conf import settings

from stretch import signals, utils, parser

log = logging.getLogger('stretch')


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

    def pull(self, options={}):
        """
        Pull the latest version of the code according to the given
        `options`.

        Returns a path to the newly-pulled code.

        :Parameters:
          - `options`: optional dictionary that specifies what to pull.
        """
        raise NotImplementedError  # pragma: no cover

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

    def get_snapshot(self):
        """
        Returns the path of a temporary directory containing the pulled source.
        """
        return utils.temp_dir(self.pull())


class GitRepositorySource(Source):
    """
    A source that pulls code from a git repository.
    """

    def __init__(self, options):
        super(GitRepositorySource, self).__init__(options)
        self.url = self.require_option('url')
        self.ref = None

    def pull(self, options={}):
        ref = options.get('ref')

        if not self.ref or self.ref != ref:
            self.ref = ref

            self.path = os.path.join(
                settings.STRETCH_CACHE_DIR, hashlib.sha1(self.url).hexdigest())
            log.debug('Using repo directory: %s' % self.path)

            log.debug('Checking if cached repo exists...')
            if os.path.exists(self.path):
                log.debug('Cached repo exists')
                repo = git.Repo(self.path)
                # Pull repository changes
                repo.remotes.origin.pull()
            else:
                log.debug('Cached repo doesn\'t exist')
                log.info('Cloning repo: %s' % self.url)
                # Create directory
                utils.makedirs(self.path)
                # Clone the repository into cache
                repo = git.Repo.clone_from(self.url, self.path)

            if self.ref:
                log.info('Using commit: %s' % self.ref)
                repo.head.reset(self.ref, working_tree=True)
            else:
                log.info('No commit specified.')
                log.info('Using commit: %s' % repo.head.commit.hexsha)

        else:
            log.info('Ref %s already checked out.' % self.ref)

        return self.path


class AutoloadableSource(Source):
    """
    A source that triggers a callback when its files are changed.
    """

    def __init__(self, options):
        """
        :Parameters:
          - `options`: dictionary containing source options. The
            `autoload` options determines if the source should autoload
            on file changes.
        """
        super(AutoloadableSource, self).__init__(options)
        self.autoload = self.options.get('autoload', True)
        self.on_change_callback = None

    def watch(self):
        if self.autoload:
            self.do_watch()

    def do_watch(self):
        raise NotImplementedError


class EventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super(EventHandler, self).__init__()
        self.callback = callback
        self.queue = []
        self.timeout = 0.2
        self.timer = None

    def on_any_event(self, event):
        self.queue.append(event)
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.timeout, self.push_queue)
        self.timer.start()

    def push_queue(self):
        self.callback(self.queue)
        self.queue = []


class FileSystemSource(AutoloadableSource):
    def __init__(self, options):
        super(FileSystemSource, self).__init__(options)
        self.path = self.require_option('path')

    def do_watch(self):
        log.info('Monitoring %s' % self.path)
        observer = Observer()
        observer.schedule(EventHandler(self.on_change), self.path,
                          recursive=True)
        observer.start()

    def on_change(self, events):
        # Autoload node only if an event took place within the node's
        # monitored path
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
            signals.sync_source.send(sender=self, nodes=autoload_nodes)

    def pull(self, options={}):
        return self.path


def get_sources(system):
    source_map = get_source_map(settings.STRETCH_SOURCES)
    return source_map.get(system.name, [])


def get_system(source):
    source_map = get_source_map(settings.STRETCH_SOURCES)
    for system_name, sources in source_map.iteritems():
        if source in sources:
            return system_name
    return None


def watch():
    source_map = get_source_map(settings.STRETCH_SOURCES)
    for system_name, sources in source_map.iteritems():
        for source in sources:
            if hasattr(source, 'watch'):
                source.watch()


@utils.memoized
def get_source_map(source_dict):
    source_map = {}

    for system_name, sources in source_dict.iteritems():
        source_map[system_name] = []

        for class_name, options in sources.iteritems():
            source_class = utils.get_class(class_name)
            source_map[system_name].append(source_class(options))

    return source_map
