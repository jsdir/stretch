from mock import Mock, patch
from nose.tools import eq_, raises

from stretch import models, exceptions


class TestEnvironment(object):
    @patch('stretch.backends.get_backend')
    def test_backend(self, get_backend):
        get_backend.return_value = 'foo'
        env = models.Environment(name='env')
        eq_(env.backend, 'foo')

    @patch('django.conf.settings.STRETCH_DATA_DIR', '/data')
    def test_get_config_path(self):
        env = models.Environment(name='env', id=22)
        eq_(env.get_config_path(), '/data/environments/22/config.json')

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
