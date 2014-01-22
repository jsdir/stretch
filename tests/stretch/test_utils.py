from django.utils.unittest import TestCase

from stretch import utils


class TestUtils(TestCase):

    def test_memoized(self):

        @utils.memoized
        def func():
            return object()

        self.assertEquals(func(), func())
