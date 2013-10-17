from mock import Mock, patch
from nose.tools import eq_, raises
from django.core.exceptions import ValidationError

from stretch import models, signals


class TestSingalReceivers(object):
    @patch('stretch.models.System')
    @patch('stretch.sources.get_system')
    def test_sync_source_receiver(self, get_system, system_mock):
        source = Mock()
        env1 = Mock()
        env1.has_autoloading_backend.return_value = True
        env2 = Mock()
        env2.has_autoloading_backend.return_value = False
        system = Mock()
        system.environments.all.return_value = [env1, env2]
        system_mock.objects.get.return_value = system

        signals.sync_source.send(sender=source, snapshot=Mock(), nodes=[])
        env1.autoload.delay.assert_called_with(source, [])
        assert not env2.autoload.delay.called

    @patch('stretch.models.System')
    def test_load_sources_receiver(self, system_mock):
        system = Mock()
        system_mock.objects.all.return_value = [system]
        signals.load_sources.send(sender=Mock())
        system.load_sources.assert_called_with()

    def test_release_created_receiver(self):
        release = Mock()
        env = Mock(auto_deploy=True)
        release.system.environments.all.return_value = [env]
        signals.release_created.send(sender=release)
        env.deploy.delay.assert_called_with(release)
