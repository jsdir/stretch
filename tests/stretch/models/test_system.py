from mock import Mock
from django.test import TestCase

from stretch.models import System


class TestSystem(TestCase):
    def setUp(self):
        self.system = System(name='system')

    '''
    def testCreateRelease(self):
        # Stub default source
        source = Mock()

        release = self.system.create_release({'foo': 'bar'})

        source.pull.assert_called_with({'foo': 'bar'})

        # Assert release created correctly
    '''
