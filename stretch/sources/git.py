from __future__ import absolute_import

import os
import git
import hashlib
import logging

from stretch import utils, config
from stretch.source import Source


log = logging.getLogger(__name__)


class GitRepositorySource(Source):
    """
    A source that pulls code from a git repository.
    """

    name = 'git'

    def pull(self, options):
        super(GitRepositorySource, self).pull(options)

        url = self.require_option('url')
        ref = self.options.get('ref')
        path = os.path.join(config.get_config()['cache_dir'],
                            hashlib.sha1(url).hexdigest())

        log.debug('Using repo directory: %s' % path)

        log.debug('Checking if repo is already cached...')
        if os.path.exists(path):
            log.debug('Cached repo exists')
            repo = git.Repo(path)
            # Pull repository changes
            repo.remotes.origin.pull()
        else:
            log.debug("Cached repo doesn't exist")
            log.info('Cloning repo: %s' % url)
            repo = git.Repo.clone_from(url, path)

        if ref:
            repo.head.reset(ref, working_tree=True)
        else:
            log.info('No commit specified.')
            ref = repo.head.commit.hexsha

        log.info('Using commit: %s' % ref)

        return path, ref
