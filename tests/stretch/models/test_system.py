from mock import Mock, patch
from nose.tools import eq_, raises
from testtools import TestCase

from stretch import models, exceptions


class TestSystem(TestCase):
    def setUp(self):
        super(TestSystem, self).setUp()
        self.system = models.System(name='system')

    @raises(exceptions.UndefinedSource)
    @patch('stretch.sources.get_sources')
    def test_source(self, get_sources):
        get_sources.return_value = ['foo']
        eq_(self.system.source, 'foo')
        get_sources.return_value = []
        self.system = models.System(name='bar')
        self.system.source

    @patch('stretch.config_managers.get_config_manager')
    def test_config_manager(self, get_config_manager):
        config_manager = Mock()
        get_config_manager.return_value = config_manager
        eq_(self.system.config_manager, config_manager)

    @patch('stretch.models.System.environments')
    @patch('stretch.models.System.source')
    @patch('stretch.models.Environment.backend')
    def test_initial_sync_source(self, backend, source, environments):
        source.autoload = True
        env = Mock()
        env.backend.autoloads = True
        environments.all.return_value = [env]
        self.system.sync_source()
        env.deploy.delay.assert_called_with(source)

        env.backend.autoloads = False
        env.deploy.delay.reset_mock()
        self.system.sync_source()
        assert not env.deploy.delay.called

        source.autoload = False
        env.backend.autoloads = True
        env.deploy.delay.reset_mock()
        self.system.sync_source()
        assert not env.deploy.delay.called

    @patch('stretch.models.System.environments')
    @patch('stretch.models.System.source')
    @patch('stretch.models.Environment.backend')
    def test_sync_source(self, backend, source, environments):
        source.autoload = True
        env = Mock()
        env.backend.autoloads = True
        environments.all.return_value = [env]
        self.system.sync_source(['foo', 'bar'])
        env.autoload.delay.assert_called_with(source, ['foo', 'bar'])

        env.backend.autoloads = False
        env.autoload.delay.reset_mock()
        self.system.sync_source(['foo', 'bar'])
        assert not env.autoload.delay.called

        source.autoload = False
        env.backend.autoloads = True
        env.autoload.delay.reset_mock()
        self.system.sync_source(['foo', 'bar'])
        assert not env.autoload.delay.called

    @patch('stretch.models.System.source')
    @patch('stretch.models.Release')
    def test_create_release(self, release_mock, source):
        source.pull = Mock(return_value='path')
        release = self.system.create_release({'key': 'value'})
        release_mock.create.assert_called_with('path', system=self.system)
        self.system.source.pull.assert_called_with({'key': 'value'})
