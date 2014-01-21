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

    def get_snapshot(self):
        ##### ARE THESE METHODS EVEN NECESSARY? CLEAN IT UP.
        """
        Returns the path of a temporary directory containing the pulled source.
        """
        return utils.temp_dir(self.pull())

    def create_release(self, system):
        return Release.create(self.get_snapshot(), system)


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
