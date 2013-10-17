from mock import patch
from nose.tools import eq_, raises

from stretch import models, exceptions


class TestSystem(object):
    @raises(exceptions.UndefinedSource)
    @patch('stretch.sources.get_sources')
    def test_system_source(self, get_sources):
        get_sources.return_value = ['foo']
        system = models.System(name='system')
        eq_(system.source, 'foo')
        get_sources.return_value = []
        system = models.System(name='bar')
        system.source

    def test_system_load_sources(self):
        pass