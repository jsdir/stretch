from django.utils.unittest import TestCase

from stretch import utils


class TestUtils(TestCase):

    def test_memoized(self):

        @utils.memoized
        def func():
            return object()

        self.assertEquals(func(), func())

    def test_merge(self):
        original_dict = {
            'foo': 1,
            'bar': 2,
            'fubar': {
                'a': 1
            }
        }

        utils.merge(original_dict, {
            'bar': 3,
            'foobar': 4,
            'fubar': {
                'a': 5
            }
        })

        self.assertEquals(original_dict, {
            'foo': 1,
            'bar': 3,
            'foobar': 4,
            'fubar': {
                'a': 5
            }
        })
