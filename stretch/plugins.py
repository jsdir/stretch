import os
import logging
import virtualenv
from subprocess import call
from django.conf import settings
import jinja2

from stretch import utils


log = logging.getLogger(__name__)


class PluginEnvironment(object):
    def __init__(self, env_name, version):
        self.env_name = env_name
        self.version = version


class NodePluginEnvironment(PluginEnvironment):
    def __init__(self):
        super(NodePluginEnvironment, self).__init__()
        home_dir = settings.HOME_DIR

        try:
            self.npm_path = os.environ.get['NPM_PATH']
        except KeyError:
            raise KeyError('NPM_PATH environment variable is undefined')

    def install_package(self, package, version, args=[]):
        call([self.npm_path, 'install', ' '.join(args),
              '%s@%s' % (package, version)])

    def call_npm(self, args):
        call([self.npm_path] + args)


class Plugin(object):
    def __init__(self, options, path):
        self.options = options
        self.path = path

    def setup(self):
        raise NotImplementedError

    def build(self):
        log.debug('%s build hook triggered' % self)

    def before_release_change(self, old_release, new_release, env):
        log.debug('%s before_release_change hook triggered' % self)

    def after_release_change(self, old_release, new_release, env):
        log.debug('%s after_release_change hook triggered' % self)


class MigrationsPlugin(Plugin):

    name = 'migrations'

    def __init__(self):
        super(MigrationsPlugin, self).__init__()
        self.is_setup = False

    def setup(self):
        if not self.is_setup:
            self.env = NodePluginEnvironment(self.name, None)
            self.env.install_package('db-migrate', '0.5.4')
            self.is_setup = True

    def before_release_change(self, old_release, new_release, env):
        self.setup()

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
    """
    path:    path containing the Gruntfile
    context: context to pass to the Gruntfile template
    """
    name = 'grunt'

    def __init__(self):
        super(GruntPlugin, self).__init__()
        self.is_setup = False

    def setup(self):
        if not self.is_setup:
            self.env = NodePluginEnvironment(self.name, None)
            self.env.install_package('grunt-cli', '0.1.9', ['-g'])
            self.is_setup = True

    def build(self):
        self.setup()

        path = self.options.get('path') or '.'
        context = self.options.get('context')

        grunt_path = os.path.join(self.path, path)

        # Check for Gruntfile(.js, .coffee)
        grunt_file = None

        for file_name in ('Gruntfile.js', 'Gruntfile.coffee'):
            if os.path.exists(os.path.join(grunt_path, file_name)):
                grunt_file = file_name
                break

        if not grunt_file:
            raise Exception('No Gruntfile found.')

        grunt_file_path = os.path.join(grunt_path, grunt_file)
        if context:
            # Parse Gruntfile
            loader = jinja2.loaders.FileSystemLoader(grunt_path)
            env = jinja2.Environment(loader=loader)
            data = env.get_template(grunt_file).render(context)
            with open(grunt_file_path, 'w') as grunt:
                grunt.write(data)

        # Run grunt build task
        os.chdir(grunt_file_path)
        self.env.call_npm(['install'])
        call(['grunt', 'build'])


def create_plugin(name, options, path):
    plugins = Plugin.__subclasses__()

    for plugin in plugins:
        if plugin.name == name:
            return plugin(options, path)

    return None
