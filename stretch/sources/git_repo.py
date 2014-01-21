import os
import git
import hashlib
import logging
from django.conf import settings

from stretch import utils
from stretch.source import Source


log = logging.getLogger('stretch')


class GitRepositorySource(Source):
    """
    A source that pulls code from a git repository.
    """

    def __init__(self, options):
        super(GitRepositorySource, self).__init__(options)
        self.url = self.require_option('url')

    def pull(self, options={}):
        ref = options.get('ref')
        path = os.path.join(settings.STRETCH_CACHE_DIR,
                            hashlib.sha1(self.url).hexdigest())

        log.debug('Using repo directory: %s' % path)

        log.debug('Checking if repo is already cached...')
        if os.path.exists(path):
            log.debug('Cached repo exists')
            repo = git.Repo(path)
            # Pull repository changes
            repo.remotes.origin.pull()
        else:
            log.debug("Cached repo doesn't exist")
            log.info('Cloning repo: %s' % self.url)
            # Create directory
            utils.makedirs(path)
            # Clone the repository into cache
            repo = git.Repo.clone_from(self.url, path)

        if ref:
            log.info('Using commit: %s' % ref)
            repo.head.reset(ref, working_tree=True)
        else:
            log.info('No commit specified.')
            log.info('Using commit: %s' % repo.head.commit.hexsha)

        return path
