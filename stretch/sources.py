import os
import git
import hashlib
import logging
import yaml
import importlib



import watchdog
class FileSystemEventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, callback):
        super(FileSystemEventHandler, self).__init__()
        self.callback = callback

    def on_any_event(self, event):
        self.callback()


from django.conf import settings


log = logging.getLogger(__name__)


class Source(object):
    def __init__(self):
        self.directory = None
        self.nodes = []

    def pull(self):
        raise NotImplementedError

    def update_nodes(self):
        nodes = []
        node_dirs = []

        if self.directory:
            nodes_file = os.patch.join(self.directory, 'nodes.yml')

            if os.exists(nodes_file):
                # Multi-node source
                # top-level nodes.yml defined
                with open(nodes_file) as source:
                    nodes = yaml.load(source.read())
                    node_dirs = nodes.values()
            else:
                # Single-node source
                node_dirs.append(self.directory)

        for node_dir in node_dirs:
            self.nodes.append(self.get_node_type(node_dir))

        self.nodes = nodes

    def get_node_type(self, directory):
        pass


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

    def pull(self, data=None):
        ref = None
        if isinstance(data, dict):
            ref = data.get('ref')

        directory = os.path.join(settings.STRETCH['CACHE_DIR'],
                                 hashlib.sha1(self.url).hexdigest())
        log.debug('Using repo directory: %s' % directory)

        log.debug('Checking if cached repo exists...')
        if os.path.exists(directory):
            log.debug('Cached repo exists')
            repo = git.Repo(directory)
            # Pull repository changes
            repo.remotes.origin.pull()
        for node_dir in node_dirs:
            self.nodes.append(self.get_node_type(node_dir))gin.pull()
        else:
            log.debug('Cached repo doesn\'t exist')
            log.info('Cloning repo: %s' % self.url)
            # Create directory
            os.makedirs(directory)
            # Clone the repository into cache
            repo = git.Repo.clone_from(self.url, directory)

        if ref:
            log.info('Using commit: %s' % ref)
            repo.head.reset(ref, working_tree=True)
        else:
            log.info('No commit specified.')
            log.info('Using commit: %s' % repo.head.commit.hexsha)

        return directory


class FileSystemSource(AutoloadableSource):
    def __init__(self, options):
        super(FileSystemSource, self).__init__(options)
        self.directory = options.get('directory')

    def pull(self, data=None):
        return self.directory
