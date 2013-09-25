import os
import logging
import virtualenv
from subprocess import call
from django.conf import settings
from functools import reduce

from stretch import utils, contexts


log = logging.getLogger('stretch')


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
    def __init__(self, options, parent):
        self.options = options
        self.parent = parent
        self.path = parent.path
        self.relative_path = parent.relative_path

        self.monitored_paths = map(lambda x: os.path.join(self.path, x),
                                   self.options.get('watch', []))
        if not self.monitored_paths:
            self.monitored_paths.append(self.path)

    def setup(self):
        raise NotImplementedError

    def build(self):
        log.debug('%s build hook triggered' % self)

    def pre_deploy(self, new_source, existing_source, environment):
        log.debug('%s pre_deploy hook triggered' % self)

    def post_deploy(self, new_source, existing_source, environment):
        log.debug('%s post_deploy hook triggered' % self)


class MigrationsPlugin(Plugin):
    """
    path:    path containing the migrations
    context: context to pass to database.json
    """
    name = 'migrations'

    def __init__(self):
        super(MigrationsPlugin, self).__init__()
        self.is_setup = False

    def setup(self):
        if not self.is_setup:
            self.env = NodePluginEnvironment(self.name, None)
            self.env.install_package('db-migrate', '0.5.4', ['-g'])
            self.is_setup = True

    def pre_deploy(self, new_source, existing_source, environment):
        # Migrations are done before releases are rolled out
        super(MigrationsPlugin, self).pre_deploy(new_source,
                                                 existing_source,
                                                 environment)
        self.setup()

        new_release = new_source.release
        existing_release = None
        if existing_source:
            existing_release = existing_source.release

        if (not existing_release or
                new_release.created_at > existing_release.created_at):
            self.migrate(self, new_release, existing_release, environment)
        else:
            existing_plugin = None
            for plugin in existing_release.plugins:
                if (plugin.name == self.name and
                    plugin.relative_path == self.relative_path):
                    existing_plugin = plugin

            if existing_plugin:
                self.migrate(existing_plugin, new_release, existing_release,
                             environment)
            else:
                # TODO: logger
                print "Exsiting release plugin not found. Skipping."

    def migrate(self, plugin, new_release, existing_release, environment):
        migrations_path = self.get_migrations_path(plugin)

        # Parse database.json
        database_file_path = os.path.join(migrations_path, 'database.json')

        # Render template
        contexts = [contexts.create_deploy_context(environment, new_release,
                                                   existing_release)]

        context = self.options.get('context')
        if context:
            contexts.append(context)

        utils.render_template_to_file(database_file_path, contexts=contexts)

        os.chdir(migrations_path)
        self.env.call_npm(['install'])

        if plugin == self:
            call(['db-migrate', '-e', 'stretch', 'up'])
        else:
            new_migrations_path = self.get_migrations_path(self)
            migrations = os.listdir(os.path.join(new_migrations_path,
                                                 'migrations'))
            migration_file = reduce(migrations, self.get_later_migration)
            call(['db-migrate', '-e', 'stretch', 'down', migration_file])

    def get_migrations_path(self, plugin):
        path = plugin.options.get('path', '.')
        return os.path.join(plugin.path, path)

    def get_later_migration(self, x, y):
        if int(x.split('-')[0]) > int(y.split('-')[0]):
            return x
        else:
            return y


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
        super(GruntPlugin, self).build()
        self.setup()

        grunt_path = self.path
        path = self.options.get('path')
        if path:
            grunt_path = os.path.join(grunt_path, path)

        # Check for Gruntfile
        grunt_file = None

        for file_name in ('Gruntfile.js.jinja', 'Gruntfile.coffee.jinja',
                          'Gruntfile.js', 'Gruntfile.coffee'):
            path = os.path.join(grunt_path, file_name)
            if os.path.exists(path):
                grunt_file = path
                break

        if not grunt_file:
            raise Exception('No Gruntfile found.')

        # Render template
        dest_file = None
        if grunt_file.endswith('.jinja'):
            dest_file = os.path.splitext(grunt_file)[0]
            contexts = [contexts.create_deploy_context(environment)]

            context = self.options.get('context')
            if context:
                contexts.append(context)

            utils.render_template_to_file(grunt_file, dest=dest_file,
                                          contexts=[context])

        # Run grunt build task
        os.chdir(grunt_path)
        self.env.call_npm(['install'])
        call(['grunt', 'build'])

        # Clean up
        if dest_file:
            os.remove(dest_file)


def create_plugin(name, options, parent):
    plugins = Plugin.__subclasses__()

    for plugin in plugins:
        if plugin.name == name:
            return plugin(options, parent)

    return None
