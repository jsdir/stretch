from mock import Mock, patch, DEFAULT, call
from nose.tools import eq_, assert_raises
from testtools import TestCase

from stretch import backends
from stretch.testutils import mock_attr


class TestBackendMap(object):
    @patch('stretch.backends.get_backend_map')
    def test_get_backend(self, get_backend_map):
        get_backend_map.return_value = {
            'system': {
                'env': 'foo'
            }
        }

        env = Mock()
        env.name = 'env'
        env.system = Mock()
        env.system.name = 'system'
        eq_(backends.get_backend(env), 'foo')
        env.name = 'foo'
        eq_(backends.get_backend(env), None)
        env.system.name = 'foo'
        eq_(backends.get_backend(env), None)

    @patch('stretch.utils.get_class')
    def test_get_backend_map(self, get_class):

        class TestBackend(object):
            def __init__(self, options):
                self.options = options

        get_class.return_value = TestBackend

        backend_dict = {
            'system': {
                'env': {
                    'path.to.BackendClass': {
                        'foo': 'bar',
                    }
                }
            }
        }

        backend_map = backends.get_backend_map(backend_dict)
        backend = backend_map['system']['env']
        assert isinstance(backend, TestBackend)
        eq_(backend.options, {'foo': 'bar'})


class TestRackspaceBackend(TestCase):
    def setUp(self):
        super(TestRackspaceBackend, self).setUp()

        patcher = patch('stretch.backends.pyrax')
        self.addCleanup(patcher.stop)
        self.pyrax = patcher.start()

        self.cs = Mock()
        self.cs.images.list.return_value = [mock_attr(name='image')]
        self.cs.flavors.list.return_value = [mock_attr(ram=512)]
        self.pyrax.connect_to_cloudservers.return_value = self.cs

        self.backend = backends.RackspaceBackend({
            'username': 'barfoo',
            'api_key': '------',
            'region': 'dfw',
            'domainname': 'example.com',
            'image': 'image',
            'ram': 512
        })

    def test_init(self):
        self.cs.images.list.return_value = [mock_attr(name='image22')]

        options = {
            'username': 'barfoo',
            'api_key': '------',
            'region': 'dfw',
            'domainname': 'example.com',
            'image': 'foo',
            'ram': 1
        }

        with assert_raises(backends.RackspaceBackend.ImageNotFound):
            backends.RackspaceBackend(options)

        options['image'] = 'mage2'
        with assert_raises(backends.RackspaceBackend.FlavorNotFound):
            backends.RackspaceBackend(options)

        options['ram'] = 512
        backends.RackspaceBackend(options)

        pyrax = self.pyrax
        pyrax.connect_to_cloudservers.assert_called_with(region='DFW')
        pyrax.connect_to_cloud_loadbalancers.assert_called_with(region='DFW')
        pyrax.set_credentials.assert_called_with('barfoo', '------')

    def test_should_create_image(self):
        backend = self.backend

        backend.store_images = False
        eq_(backend.should_create_image('prefix-name', 'prefix'),
            (False, None))

        backend.store_images = True
        eq_(backend.should_create_image('prefix-name', 'prefix'), (True, None))

        image = mock_attr(name='prefix-name', id='id')
        self.cs.images.list.return_value = [image]
        eq_(backend.should_create_image('prefix-name', 'prefix'),
            (False, 'id'))

        im1 = mock_attr(name='prefix-foo')
        im2 = mock_attr(name='otherprefix-foo')
        self.cs.images.list.return_value = [im1, im2]
        backend.store_images = False
        backend.should_create_image('prefix-name', 'prefix')

        assert not im1.delete.called
        assert not im2.delete.called

        backend.store_images = True
        backend.should_create_image('prefix-name', 'prefix')

        im1.delete.assert_called_with()
        assert not im2.delete.called

    @patch('stretch.backends.get_image_name', return_value=('p-name', 'p'))
    @patch('stretch.backends.RackspaceBackend.should_create_image')
    @patch('stretch.backends.RackspaceBackend.provision_host')
    def test_create_host(self, provision_host, should_create_image, get_name):
        server = mock_attr(status='ACTIVE', accessIPv4='publicip',
                           networks={'private': ['privateip']})
        self.cs.servers.create.return_value = server
        host = Mock()

        should_create_image.return_value = (True, 'id')
        self.backend.use_public_network = True
        self.backend.create_host(host)
        provision_host.assert_called_with(server, 'publicip', host, True,
                                          'p-name', 'p')

        should_create_image.return_value = (False, None)
        self.backend.use_public_network = False
        self.backend.create_host(host)
        provision_host.assert_called_with(server, 'privateip', host, False,
                                          'p-name', 'p')

    @patch.multiple('stretch.backends', put=DEFAULT, run=DEFAULT,
                    upload_template=DEFAULT, env=DEFAULT)
    def test_provision_host(self, put, run, upload_template, env):
        s = Mock()
        s.adminPass = 'password'
        s.create_image.return_value = 'imageid'
        host = Mock()
        self.cs.images.get.return_value = mock_attr(status='ACTIVE')

        self.backend.provision_host(s, '0.0.0.0', host, True, 'p-name', 'p')
        eq_(env.host_string, 'root@0.0.0.0')
        eq_(env.password, 'password')
        run.assert_has_calls([call('/bin/bash image-bootstrap.sh'),
                              call('/bin/bash /root/host-bootstrap.sh')])
        run.reset()

        self.backend.provision_host(s, '0.0.0.0', host, False, 'p-name', 'p')
        run.assert_called_with('/bin/bash /root/host-bootstrap.sh')


class TestBackend(object):
    @patch('stretch.__version__', '0.2')
    @patch('django.conf.settings.STRETCH_BACKEND_IMAGE_PREFIX', 'prefix')
    def test_get_image_name(self):
        eq_(backends.get_image_name(), ('prefix-0.2', 'prefix'))
