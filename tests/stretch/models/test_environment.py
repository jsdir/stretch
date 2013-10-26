from mock import patch, Mock
from nose.tools import eq_
from unittest import TestCase

from stretch import models


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
