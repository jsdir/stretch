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

    def pre_deploy(self, environment, new_parser, existing_parser):
        log.debug('%s pre_deploy hook triggered' % self)

    def post_deploy(self, environment, new_parser, existing_parser):
        log.debug('%s post_deploy hook triggered' % self)

    def get_path(self):
        full_path = self.path
        path = self.options.get('path')

        if path:
            full_path = os.path.join(full_path, path)

        return full_path

    def render_template(file_names, path, contexts):
        # Check for template file
        template = None

        for file_name in ['%s.jinja' % name for name in file_names]:
            file_path = os.path.join(path, file_name)
            if os.path.exists(file_path):
                template = file_path
                break

        if not template:
            raise Exception('No template %s found.' % all_file_names)

        # Render template
        dest_file = os.path.splitext(template)[0]
        utils.render_template_to_file(template, dest=dest_file,
                                      contexts=contexts)

        return dest_file


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

    def pre_deploy(self, environment, new_parser, existing_parser):
        super(MigrationsPlugin, self).pre_deploy(environment, new_parser,
                                                 existing_parser)
        self.setup()
        self.migrate(environment, new_parser, existing_parser, pre_deploy=True)

    def post_deploy(self, environment, new_parser, existing_parser):
        super(MigrationsPlugin, self).post_deploy(environment, new_parser,
                                                  existing_parser)
        self.setup()
        self.migrate(environment, new_parser, existing_parser,
                     pre_deploy=False)

    def migrate(self, environment, new_parser, existing_parser, pre_deploy):
        if new_parser.release:
            # Standard deploy
            # Get releases
            new_release = new_parser.release
            existing_release = None
            if existing_parser:
                existing_release = existing_parser.release

            # Determine migration data to use
            if (not existing_release or
                    new_release.created_at > existing_release.created_at and
                    pre_deploy):
                # Release deploy
                # Migrate using the new release plugin
                self.run_migration(environment, self, new_release,
                                   existing_release)
            elif not pre_deploy:
                # Rollback deploy
                # Use the existing release
                # Find corresponding plugin in existing release
                existing_plugin = None
                for plugin in existing_parser.plugins:
                    if (plugin.name == self.name and
                            plugin.relative_path == self.relative_path):
                        existing_plugin = plugin

                if existing_plugin:
                    # Migrate using the existing release plugin
                    self.run_migration(environment, existing_plugin,
                                       new_release, existing_release)
                else:
                    # Leave the database alone since the rollback
                    # has no data about it
                    log.info('Migration plugin not found in rollback release. '
                             'Skipping.')

    def run_migration(self, environment, plugin, new_release, existing_release):
        path = plugin.get_path()

        # Use releases for template context
        contexts = [contexts.create_deploy_context(
            environment, new_release, existing_release)]

        # Render database.json
        context = self.options.get('context')
        if context:
            contexts.append(context)

        rendered_file = self.render_template(('database.json',), path,
                                             contexts)

        # Install dependencies and database drivers
        os.chdir(path)
        self.env.call_npm(['install'])

        if plugin == self:
            call(['db-migrate', '-e', 'stretch', 'up'])
        else:
            migrations = os.listdir(os.path.join(self.get_path(),
                                                 'migrations'))
            migration_file = reduce(migrations, self.get_later_migration)
            call(['db-migrate', '-e', 'stretch', 'down', migration_file])

        # Clean up
        os.remove(rendered_file)

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

    def build(self, environment):
        super(GruntPlugin, self).build()
        self.setup()

        path = self.get_path()

        # Render Gruntfile
        contexts = [contexts.create_deploy_context(environment)]
        context = self.options.get('context')
        if context:
            contexts.append(context)

        rendered_file = self.render_template(
            ('Gruntfile.js', 'Gruntfile.coffee'), path, contexts)

        # Run grunt build task
        os.chdir(path)
        self.env.call_npm(['install'])
        call(['grunt', 'build'])

        # Clean up
        os.remove(rendered_file)


def create_plugin(name, options, parent):
    plugins = Plugin.__subclasses__()

    for plugin in plugins:
        if plugin.name == name:
            return plugin(options, parent)

    return None
