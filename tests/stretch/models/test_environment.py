from mock import patch, Mock
from nose.tools import eq_, assert_raises
from unittest import TestCase

from stretch import models, testutils


class TestEnvironment(TestCase):
    def setUp(self):
        self.env = models.Environment(name='env')

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

    def test_check_release(self):
        release = testutils.mock_attr(sha='sha')
        source = Mock(spec=['pull'], pull=Mock())
        assert self.env.check_release(release)
        assert not self.env.check_release(source)
        with assert_raises(TypeError):
            self.env.check_release('')

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

        foo_instance.reload.assert_called_with(remember=False)
        assert not bar_instance.reload.called
        source.run_build_plugins.assert_called_with(deploy, nodes)
        mock_deploy.create.assert_called_with(environment=self.env)

    """
    def test_update_config(self):
        env = models.Environment(name='env')
        env.update_config()
        # assert all instances updates

    def test_autoload(self):
        pass

        env = models.Environment(name='env')
        env.update_config()
        # assert all instances updates

    @patch('celery.current_task', Mock())
    def test_deploy_release(self):
        system = models.System(name='system')
        system.save()
        env = models.Environment(name='env', system=system)
        env.using_source = True
        env.save()

        release = models.Release(name='rel', sha='abc', system=system)
        release.save()
        env.deploy(release)

        deploy = models.Deploy.objects.get()
        eq_(deploy.existing_release, None)
        eq_(deploy.release, release)
        #assert not env.using_source
        #eq_(env.current_release, release)

    def test_deploy_source(self):
        pass

        env = models.Environment(name='env')
        env.using_source = False
        env.current_release = Mock()
        source = Mock()
        env.deploy(source)
        assert env.using_source
        eq_(env.current_release, None)


    def test_map_instances(self):
        pass # plenty of assertions """
