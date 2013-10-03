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
        }
    })
