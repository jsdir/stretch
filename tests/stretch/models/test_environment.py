from mock import patch, Mock, MagicMock
from nose.tools import eq_, assert_raises
from unittest import TestCase

from stretch import models, testutils


class TestEnvironment(TestCase):
    def setUp(self):
        self.system = models.System()
        self.env = models.Environment(name='env', system=self.system)

    @patch('stretch.backends.get_backend')
    def test_backend(self, get_backend):
        get_backend.return_value = 'foo'
        eq_(self.env.backend, 'foo')

    @patch('django.conf.settings.STRETCH_BATCH_SIZE', 3)
    @patch('stretch.models.Environment.instances')
    @patch('stretch.utils.map_groups')
    def test_map_instances(self, map_groups, instances):
        callback = Mock()
        i_foo = Mock(spec=['group'], group='foo')
        i_bar = Mock(spec=['group'], group='bar')
        instances.all.return_value = [i_foo, i_bar]
        self.env.map_instances(callback)
        map_groups.assert_called_with(callback,
                                      {'foo': [i_foo], 'bar': [i_bar]}, 3)

    @patch('stretch.models.Environment.current_release')
    @patch('stretch.models.Deploy')
    def test_save_deploy(self, mock_deploy, current_release):
        task = Mock()
        release = Mock()

        deploy = self.env.save_deploy(task, release)
        mock_deploy.create.assert_called_with(
            environment=self.env,
            existing_release=current_release,
            release=release,
            task_id=task.request.id
        )
        deploy.save.assert_called_with()

    @patch('stretch.models.Deploy')
    @patch('stretch.models.Environment.instances')
    def test_autoload(self, instances, mock_deploy):
        mock_attr = testutils.mock_attr
        deploy = Mock()
        mock_deploy.create.return_value = deploy
        source = Mock()
        nodes = [mock_attr(name='foo')]
        foo_instance = mock_attr(node=mock_attr(name='foo'))
        bar_instance = mock_attr(node=mock_attr(name='bar'))
        instances.all.return_value = [foo_instance, bar_instance]
        self.env.autoload(source, nodes)

        foo_instance.reload.assert_called_with()
        assert not bar_instance.reload.called
        source.run_build_plugins.assert_called_with(deploy, nodes)
        mock_deploy.create.assert_called_with(environment=self.env)

    @patch('django.conf.settings.STRETCH_CACHE_DIR', '/cache')
    def test_deploy_to_instances(self):
        # TODO: fill partial test
        snapshot = MagicMock()
        self.env.pk = 24
        self.env.map_instances = Mock()
        self.env.deploy_to_instances(snapshot, sha='sha')
        snapshot.mount_templates.assert_called_with('/cache/templates/24')
        eq_(self.env.map_instances.call_count, 1)

    @patch('stretch.models.Environment.save_deploy')
    def test_deploy_source(self, save_deploy):
        deploy = MagicMock()
        save_deploy.return_value = deploy

        self.env.save = Mock()
        self.env.deploy_to_instances = Mock()
        source = Mock(spec=['pull', 'get_snapshot'])

        snapshot = Mock()
        snapshot.nodes = [1, 2]
        source.get_snapshot.return_value = snapshot

        self.env.deploy(source)
        snapshot.build_and_push.assert_called_with(None, self.system)
        self.env.deploy_to_instances.assert_called_with(snapshot, nodes=[1, 2])
        eq_(self.env.current_release, None)
        eq_(self.env.using_source, True)
        self.env.save.assert_called_with()
        deploy.start.assert_called_with(snapshot)

    @patch('stretch.models.Environment.save_deploy')
    @patch('stretch.models.Environment.current_release')
    def test_deploy_release(self, current_release, save_deploy):
        current_release.get_snapshot.return_value = existing_snapshot = Mock()
        deploy = MagicMock()
        save_deploy.return_value = deploy

        self.env.save = Mock()
        self.env.deploy_to_instances = Mock()
        release = Mock(spec=['sha', 'get_snapshot'])
        release.sha = 'sha'
        release.get_snapshot.return_value = snapshot = Mock()

        self.env.deploy(release)
        self.env.deploy_to_instances.assert_called_with(snapshot, sha='sha')
        eq_(self.env.current_release, release)
        eq_(self.env.using_source, False)
        self.env.save.assert_called_with()
        deploy.start.assert_called_with(snapshot)
        eq_(deploy.existing_snapshot, existing_snapshot)
