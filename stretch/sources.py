import os
import git
import hashlib
from django.conf import settings


class Source(object):
    def __init__(self):
        pass

    def pull(data=None):
        return None


class Autoloadable(object):
    pass


class GitRepositorySource(Source):
    """
    local_settings.py
    -----------------

    SOURCE = sources.GitRepositorySource('git://localhost/repo.git')
    """
    def __init__(self, repo_url):
        super(GitRepositorySource, self).__init__()
        self.repo_url = repo_url

    def pull(self, data=None):
        ref = None
        if isinstance(data, dict):
            ref = data.get('ref')

        directory = os.path.join(settings.STRETCH['CACHE_DIR'],
                                 hashlib.sha1(self.repo_url).hexdigest())
        if os.path.exists(directory):
            # Cached repo already exists
            repo = git.Repo(directory)
            # Pull repository changes
            repo.remotes.origin.pull()
        else:
            # Create directory
            os.makedirs(directory)
            # Clone the repository into cache
            repo = git.Repo.clone_from(self.repo_url, directory)

        if ref:
            # INFO: Using commit %(ref)s
            repo.head.reset(ref, working_tree=True)
        else:
            pass
            # WARNING: no ref specified, using repo.head.commit.hexsha

        return directory


class FileSystemSource(Source, Autoloadable):
    """
    local_settings.py
    -----------------

    SOURCE = sources.FileSystemSource('/location/of/codebase')
    """
    def __init__(self, directory):
        super(FileSystemSource, self).__init__()
        self.directory = directory

    def pull(data=None):
        return self.directory
