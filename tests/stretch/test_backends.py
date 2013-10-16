from mock import Mock, patch
from nose.tools import eq_

from stretch import backends


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
