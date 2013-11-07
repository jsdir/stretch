from mock import patch, Mock, MagicMock, DEFAULT
from nose.tools import eq_, assert_raises, raises
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

    """
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
                                      {'foo': [i_foo], 'bar': [i_bar]}, 3)"""

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

    @patch('stretch.models.current_task', 'task')
    @patch.multiple('stretch.models.Environment', save_deploy=DEFAULT,
                    deploy_obj=DEFAULT)
    def test_deploy_source(self, save_deploy, deploy_obj):
        source = Mock(spec=['pull'])
        deploy = Mock()
        save_deploy.return_value = deploy

        self.env.deploy(source)

        save_deploy.assert_called_with('task')
        deploy_obj.assert_called_with(source, deploy)
        eq_(self.env.current_release, None)
        eq_(self.env.using_source, True)

    @patch('stretch.models.current_task', 'task')
    @patch.multiple('stretch.models.Environment', save_deploy=DEFAULT,
                    deploy_obj=DEFAULT, current_release=DEFAULT)
    def test_deploy_release(self, save_deploy, deploy_obj, current_release):
        release = Mock(spec=['sha'])
        deploy = Mock()
        save_deploy.return_value = deploy

        snapshot = Mock()
        current_release.get_snapshot.return_value = snapshot
        self.env.deploy(release)

        save_deploy.assert_called_with('task', release)
        deploy_obj.assert_called_with(release, deploy)
        eq_(deploy.existing_snapshot, snapshot)
        eq_(self.env.current_release, release)
        eq_(self.env.using_source, False)

    @raises(Exception)
    def test_deploy_incompatible_object_fails(self):
        obj = Mock(spec=[])
        self.env.deploy(obj)

    @patch.multiple('stretch.models.Environment', save=DEFAULT,
                    deploy_to_instances=DEFAULT)
    def test_deploy_obj_source(self, save, deploy_to_instances):
        source = Mock()
        snapshot = Mock()
        snapshot.get_app_paths.return_value = ['a']
        source.get_snapshot.return_value = snapshot
        deploy = MagicMock()
        self.env.using_source = True
        self.env.deploy_obj(source, deploy)
        deploy_to_instances.assert_called_with()
        save.assert_called_with()
        eq_(self.env.app_paths, ['a'])
        snapshot.build_and_push.assert_called_with(None, self.system)

    @patch.multiple('stretch.models.Environment', save=DEFAULT,
                    deploy_to_instances=DEFAULT)
    def test_deploy_obj_release(self, save, deploy_to_instances):
        release = Mock()
        deploy = MagicMock()
        self.env.using_source = False
        release.sha = 'sha'
        self.env.deploy_obj(release, deploy)
        deploy_to_instances.assert_called_with('sha')
        save.assert_called_with()

    def test_post_save_created(self):
        env = Mock()
        config_manager = env.system.config_manager
        self.env.post_save(Mock(), env, True)
        config_manager.add_env.assert_called_with(env)
        config_manager.sync_env_config.assert_called_with(env)

    def test_post_save_created(self):
        env = Mock()
        config_manager = env.system.config_manager
        self.env.post_save(Mock(), env, False)
        config_manager.sync_env_config.assert_called_with(env)
