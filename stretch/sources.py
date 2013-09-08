import os
import git
import hashlib
import logging
import importlib


"""
import watchdog
class FileSystemEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, callback):
        super(FileSystemEventHandler, self).__init__()
        self.callback = callback

    def on_any_event(self, event):
        self.callback()"""


from django.conf import settings


log = logging.getLogger(__name__)


class Source(object):
    def __init__(self):
        self.path = None
        # self.nodes = []

    def pull(self, options=None):
        raise NotImplementedError

    def get_path(self):
        raise NotImplementedError


class AutoloadableSource(Source):
    """
    A source that pushes to a compatible backend on a trigger
    """
    def __init__(self, options):
        super(AutoloadableSource, self).__init__()
        self.autoload = options.get('autoload')
        self.restart_services = options.get('restart_services')

    def monitor(self):
        if self.autoload:
            if self.directory.is_changed:
                self.on_filesystem_change()

    def on_autoload(self):
        raise NotImplementedError


class GitRepositorySource(Source):
    def __init__(self, options):
        super(GitRepositorySource, self).__init__()
        self.url = options.get('url')
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
            #for node_dir in node_dirs:
            #    self.nodes.append(self.get_node_type(node_dir))
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


class FileSystemSource(AutoloadableSource):
    def __init__(self, options):
        super(FileSystemSource, self).__init__(options)
        self.path = options.get('path')

    def get_path(self):
        return self.path

    def pull(self, options=None): pass
