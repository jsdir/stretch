import os
import git
import hashlib
import logging
import importlib
import threading
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer
from django.conf import settings

import stretch
from stretch.parser import SourceParser
from stretch.models import Environment


log = logging.getLogger('stretch')
auto_deploy_environments = Environment.objects.filter(auto_deploy=True)


class Source(object):
    def __init__(self, options):
        self.path = None
        self.parser = None
        self.options = options

    def pull(self, options=None):
        raise NotImplementedError

    def get_path(self):
        raise NotImplementedError

    def parse(self):
        self.existing_parser = self.parser
        self.parser = SourceParser(self.path)
        return self.parser


class AutoloadableSource(Source):
    """
    A source that pushes to a compatible backend on a trigger
    """
    def __init__(self):
        super(AutoloadableSource, self).__init__()
        self.autoload = self.options.get('autoload') or True

    def monitor(self):
        if self.autoload:
            self.do_monitor()

    def do_monitor(self):
        raise NotImplementedError

    def deploy(self):
        for environment in auto_deploy_environments:
            environment.deploy(self)


class GitRepositorySource(Source):
    def __init__(self):
        super(GitRepositorySource, self).__init__()
        self.url = self.options.get('url')
        self.path = None

    def get_path(self):
        if not self.path:
            self.pull()
        return self.path

    def pull(self, options=None):
        ref = None
        if isinstance(options, dict):
            ref = options.get('ref')

        self.path = os.path.join(settings.CACHE_DIR,
                                 hashlib.sha1(self.url).hexdigest())
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
            os.makedirs(self.path)
            # Clone the repository into cache
            repo = git.Repo.clone_from(self.url, self.path)

        if ref:
            log.info('Using commit: %s' % ref)
            repo.head.reset(ref, working_tree=True)
        else:
            log.info('No commit specified.')
            log.info('Using commit: %s' % repo.head.commit.hexsha)


class EventHandler(FileSystemEventHandler):
    def __init__(self, source):
        super(FileSystemEventHandler, self).__init__()
        self.source = source
        self.queue = []
        self.timer = None

    def on_any_event(self, event):
        self.queue.append(event)
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(0.2, self.push_queue)
        self.timer.start()

    def push_queue(self):
        self.source.on_files_change(self.queue)
        self.queue = []


class FileSystemSource(AutoloadableSource):
    def __init__(self):
        super(FileSystemSource, self).__init__()
        self.path = self.options.get('path')
        self.parse()

    def get_path(self):
        return self.path

    def do_monitor(self):
        log.info('Monitoring %s' % self.path)
        event_handler = EventHandler(self)
        observer = Observer()
        observer.schedule(event_handler, self.path, recursive=True)
        observer.start()

    def on_files_change(self, file_events):
        self.parse()

        for environment in auto_deploy_environments:
            environment.autoload(self, self.existing_parser, self.parser,
                                 file_events)

    def pull(self, options=None): pass
