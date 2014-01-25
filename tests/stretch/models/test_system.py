from mock import Mock, patch
from nose.tools import raises
from django.test import TestCase
from django.test.utils import override_settings


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

    @override_settings(STRETCH_STASHES={'sys3': '/stash'})
    def test_stash_path(self):
        system = System(name='sys3')
        self.assertEquals(system.stash_path, '/stash')
