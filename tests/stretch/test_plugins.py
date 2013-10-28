from mock import Mock, patch
from nose.tools import eq_, assert_raises
from unittest import TestCase

from stretch import plugins
from stretch.testutils import mock_attr, check_items_equal


class TestNodePluginEnvironment(TestCase):
    @patch('stretch.plugins.call')
    def test_init(self, call):
        with patch('stretch.plugins.os') as mock_os:
            mock_os.environ = {}
            with assert_raises(KeyError):
                plugins.NodePluginEnvironment()
            mock_os.environ = {'NPM_PATH': '/foo/npm'}
            env = plugins.NodePluginEnvironment()

        env.install_package('package', '0.1.0')
        call.assert_called_with(['/foo/npm', 'install', 'package@0.1.0'])
        env.install_package('package', '0.1.0', ['-g', '-o'])
        call.assert_called_with(['/foo/npm', 'install', '-g', '-o',
                                 'package@0.1.0'])
        env.call_npm(['install'])
        call.assert_called_with(['/foo/npm', 'install'])


class TestPlugin(TestCase):
    def setUp(self):
        self.plugin = plugins.Plugin({
            'path': 'c/d',
            'watch': ['e/f', 'g/h']
        }, mock_attr(path='/a/b'))

    def test_monitored_paths(self):
        check_items_equal(self.plugin.monitored_paths,
                          ['/a/b/e/f', '/a/b/g/h'])

        plugin = plugins.Plugin({}, mock_attr(path='/a/b'))
        eq_(plugin.monitored_paths, ['/a/b'])

    def test_get_path(self):
        eq_(self.plugin.get_path(), '/a/b/c/d')
        self.plugin.options = {}
        eq_(self.plugin.get_path(), '/a/b')

    @patch('stretch.utils.render_template_to_file')
    def test_render_template(self, render_template_to_file):

        def exists(path):
            return path == '/foo/t.jinja'

        contexts = Mock()

        with patch('stretch.plugins.os.path.exists', exists):
            dest = plugins.Plugin.render_template(['a', 't'], '/foo', contexts)
            eq_(dest, '/foo/t')
            render_template_to_file.assert_called_with('/foo/t.jinja',
                dest='/foo/t', contexts=contexts)

        with patch('stretch.plugins.os.path.exists', return_value=False):
            with assert_raises(NameError):
                plugins.Plugin.render_template(['a', 't'], '/foo', contexts)


class TestMigrationsPlugin(object):
    def setUp(self):
        self.plugin = plugins.MigrationsPlugin({}, Mock())

    @patch('stretch.plugins.NodePluginEnvironment', Mock())
    def test_setup(self):
        self.plugin.setup()
        self.plugin.env.install_package.assert_called_with('db-migrate',
                                                           '0.5.4', ['-g'])
        assert self.plugin.is_setup

    def test_pre_deploy(self):
        deploy = Mock()
        self.plugin.migrate = Mock()
        with patch.object(self.plugin, 'setup'):
            self.plugin.pre_deploy(deploy)
            self.plugin.migrate.assert_called_with(deploy, pre_deploy=True)
            self.plugin.setup.assert_called_with()

    def test_post_deploy(self):
        deploy = Mock()
        self.plugin.migrate = Mock()
        with patch.object(self.plugin, 'setup'):
            self.plugin.post_deploy(deploy)
            self.plugin.migrate.assert_called_with(deploy, pre_deploy=False)
            self.plugin.setup.assert_called_with()

    def test_get_later_migration(self):
        eq_(self.plugin.get_later_migration('1-migration.js',
            '2-migration.js'), '2-migration.js')
        eq_(self.plugin.get_later_migration('2000-migration.js',
            '1000-migration.js'), '2000-migration.js')

    def test_migrate(self):
        deploy = Mock()
        #self.plugin.migrate(deploy, True)
        #self.plugin.migrate(deploy, False)

    def test_run_migration(self):
        pass


class TestGruntPlugin(object):
    def test_pre_deploy(self):
        plugin = plugins.GruntPlugin({}, Mock())


@patch('stretch.plugins.Plugin.__subclasses__')
def test_create_plugin(subc):
    plugin = mock_attr(name='plugin_name')
    subc.return_value = [plugin, mock_attr(name='foo')]
    options, parent = Mock(), Mock()
    result_plugin = plugins.create_plugin('plugin_name', options, parent)
    plugin.assert_called_with(options, parent)
    eq_(result_plugin, plugin())
    eq_(plugins.create_plugin('undefined', options, parent), None)
