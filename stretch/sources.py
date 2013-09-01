import os
import git
import hashlib
import logging
import yaml



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
        


class AutoloadableSource(Source):
    def __init__(self):
        super(AutoloadableSource, self).__init__()
        self.restart_services = False

    def monitor(self):
        if self.restart_services and self.directory:
            # Setup filesystem monitoring
            if self.directory changed:
                self.on_filesystem_change()

    def on_filesystem_change(self):
        raise NotImplementedError


class GitRepositorySource(Source):
    def __init__(self, repo_url):
        super(GitRepositorySource, self).__init__()
        self.repo_url = repo_url

    def pull(self, data=None):
        ref = None
        if isinstance(data, dict):
            ref = data.get('ref')

        directory = os.path.join(settings.STRETCH['CACHE_DIR'],
                                 hashlib.sha1(self.repo_url).hexdigest())
        log.debug('Using repo directory: %s' % directory)

        log.debug('Checking if cached repo exists...')
        if os.path.exists(directory):
            log.debug('Cached repo exists')
            repo = git.Repo(directory)
            # Pull repository changes
            repo.remotes.origin.pull()
        else:
            log.debug('Cached repo doesn\'t exist')
            log.info('Cloning repo: %s' % self.repo_url)
            # Create directory
            os.makedirs(directory)
            # Clone the repository into cache
            repo = git.Repo.clone_from(self.repo_url, directory)

        if ref:
            log.info('Using commit: %s' % ref)
            repo.head.reset(ref, working_tree=True)
        else:
            log.info('No commit specified.')
            log.info('Using commit: %s' % repo.head.commit.hexsha)

        return directory


class FileSystemSource(AutoloadableSource):
    def __init__(self, directory):
        super(FileSystemSource, self).__init__()
        self.directory = directory

    def pull(self, data=None):
        return self.directory
