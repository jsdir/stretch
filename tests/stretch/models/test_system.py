from mock import Mock, patch
from nose.tools import raises
from django.test import TestCase

from stretch.models import System
from stretch import source


class TestSystem(TestCase):

    @patch('stretch.source.get_sources')
    def test_source(self, get_sources):
        system = System(name='sys1')
        get_sources.return_value = ['foo']
        self.assertEquals(system.source, 'foo')

    @raises(source.NoSourceException)
    @patch('stretch.source.get_sources')
    def test_source_fails(self, get_sources):
        system = System(name='sys2')
        get_sources.return_value = []
        system.source
