from mock import Mock, patch
from nose.tools import eq_, raises
from django.core.exceptions import ValidationError

from stretch import models, signals


class TestSingalReceivers(object):
    @patch('stretch.models.System')
    @patch('stretch.sources.get_system')
    def test_sync_source_receiver(self, get_system, system_mock):
        get_system.return_value = 'system'
        system = Mock()
        system_mock.objects.get.return_value = system
        signals.sync_source.send(sender=Mock(), nodes=['node1', 'node2'])
        system.sync_source.assert_called_with(['node1', 'node2'])

    @patch('stretch.models.System')
    def test_load_sources_receiver(self, system_mock):
        system = Mock()
        system_mock.objects.all.return_value = [system]
        signals.load_sources.send(sender=Mock())
        system.sync_source.assert_called_with()

    def test_release_created_receiver(self):
        release = Mock()
        env = Mock(auto_deploy=True)
        release.system.environments.all.return_value = [env]
        signals.release_created.send(sender=release)
        env.deploy.delay.assert_called_with(release)
