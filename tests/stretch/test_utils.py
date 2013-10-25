from mock import Mock, patch
from nose.tools import eq_, assert_raises
import errno

from stretch import utils, testutils


def test_update():
    d = {
        'foo': 1,
        'bar': 2,
        'fubar': {
            'a': 1
        }
    }

    utils.update(d, {
        'bar': 3,
        'foobar': 4,
        'fubar': {
            'a': 5
        }
    })

    eq_(d, {
        'foo': 1,
        'bar': 3,
        'foobar': 4,
        'fubar': {
            'a': 5
        }})


def test_memoized():

    @utils.memoized
    def func():
        return object()

    eq_(func(), func())


@patch('stretch.utils.importlib')
def test_get_class(importlib):
    importlib.import_module.return_value = testutils.mock_attr(klass='foo')
    eq_(utils.get_class('path.to.klass'), 'foo')
    importlib.import_module.assert_called_with('path.to')


@patch('stretch.utils.os')
def test_makedirs(mock_os):

    def mock_makedirs(path):
        err = OSError()
        err.errno = errno.EEXIST
        raise err

    mock_os.path.isdir.return_value = True
    mock_os.makedirs = mock_makedirs
    utils.makedirs('/foo')

    mock_os.path.isdir.return_value = False
    with assert_raises(OSError):
        utils.makedirs('/foo')

    def mock_makedirs(path):
        err = OSError()
        err.errno = 'other'
        raise err

    mock_os.makedirs = mock_makedirs
    mock_os.path.isdir.return_value = True
    with assert_raises(OSError):
        utils.makedirs('/foo')


@patch('stretch.utils.random.choice', return_value='a')
def test_generate_random_hex(choice):
    eq_(utils.generate_random_hex(2), 'aa')
    eq_(utils.generate_random_hex(4), 'aaaa')




# Test start to finish of all 4 source to backend transfer methods,
# - if signals are triggered
# - autoloading environments, systems, get_sources, get_backends
