from nose.tools import eq_

from stretch import utils


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

# Test start to finish of all 4 source to backend transfer methods,
# - if signals are triggered
# - autoloading environments, systems, get_sources, get_backends
