from django.utils.unittest import TestCase

from stretch.models import System


class TestSystem(TestCase):
    def setUp(self):
        self.system = System(name='system')

    def testCreateRelease(self):
        # Stub default source
        release = self.system.create_release({'foo': 'bar'})
        # Assert source called with {'foo': 'bar'}
        # Assert release created correctly
