import os
import logging
import virtualenv
from subprocess import call
from django.conf import settings

from stretch import utils


log = logging.getLogger(__name__)


class PluginEnvironment(object):
    def __init__(self, env_name, version):
        self.env_name = env_name
        self.version = version


class NodePluginEnvironment(PluginEnvironment):
    def __init__(self):
        super(NodePluginEnvironment, self).__init__()
        home_dir = settings.STRETCH['HOME_DIR']

        try:
            self.npm_path = os.environ.get['NPM_PATH']
        except KeyError:
            raise KeyError('NPM_PATH environment variable is undefined')

    def install_package(self, package, version, args=[]):
        call([self.npm_path, 'install', ' '.join(args),
              '%s@%s' % (package, version)])


class Plugin(object):
    def before_release_change(self, old_release, new_release, env):
        log.debug('%s before_release_change hook triggered' % self)

    def after_release_change(self, old_release, new_release, env):
        log.debug('%s after_release_change hook triggered' % self)


class MigrationsPlugin(Plugin):
    def __init__(self):
        super(MigrationsPlugin, self).__init__()
        self.name = 'migrations'
        self.env = NodePluginEnvironment(self.name, None)
        self.env.install_package('db-migrate', '0.5.4')

    def before_release_change(self, old_release, new_release, env):
        # Migrations are done before releases are rolled out
        super(MigrationsPlugin, self).before_release_change(old_release,
            new_release, env)

        # Use the newer release for the more extensive migration data
        if old_release.created_at > new_release.created_at:
            release = old_release
        else:
            release = new_release

        release


class GruntPlugin(Plugin):
    def __init__(self):
        super(GruntPlugin, self).__init__()
        self.name = 'grunt'
        self.env = NodePluginEnvironment(self.name, None)
        self.env.install_package('grunt-cli', '0.1.9', ['-g'])
