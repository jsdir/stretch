import time
from mock import Mock, patch, call
from nose.tools import raises
from django.test import TestCase

from stretch import source


class TestSource(TestCase):
    def setUp(self):
        self.src = source.Source({'foo': 'bar'})

    def test_get_option(self):
        self.assertEquals(self.src.get_option('a'), None)
        self.assertEquals(self.src.get_option('foo'), 'bar')

    def test_require_option(self):
        self.assertEquals(self.src.require_option('foo'), 'bar')

    @raises(NameError)
    def test_require_option_fails(self):
        self.src.require_option('a')


class TestLiveSource(TestCase):
    def setUp(self):
        self.source = source.LiveSource({})

    def test_is_live_by_default(self):
        self.assertEquals(self.source.is_live, True)

    def test_watch_fails_when_not_live(self):
        src = source.LiveSource({'live': False})
        src.watch = Mock()
        src.start_watch()
        assert not src.watch.called

    def test_watch_runs_when_live(self):
        src = source.LiveSource({'live': True})
        src.watch = Mock()
        src.start_watch()
        assert src.watch.was_called

    @patch('stretch.source.LiveSource._on_files_change')
    def test_buffering(self, _on_files_change):
        src = source.LiveSource({'flush': 0.02})

        src.on_file_change(1)
        time.sleep(0.01)
        src.on_file_change(2)
        time.sleep(0.03)
        src.on_file_change(1)
        time.sleep(0.03)

        _on_files_change.assert_has_calls([call([1, 2]), call([1])])

    def test_files_change(self):
        self.source._on_files_change([])


class TestSourceMap(TestCase):
    @patch('stretch.source.get_source_map')
    def test_get_sources(self, get_source_map):
        get_source_map.return_value = {'system': ['foo']}
        system = Mock()
        system.name = 'system'
        self.assertEquals(source.get_sources(system), ['foo'])
        system = Mock()
        system.name = 'bar'
        self.assertEquals(source.get_sources(system), [])

    @patch('stretch.source.get_source_map')
    def test_watch(self, get_source_map):
        src = Mock()
        src.is_live = False
        live_source = Mock()
        live_source.is_live = True
        get_source_map.return_value = {'system': [src, live_source]}
        source.watch()
        assert not src.start_watch.called
        live_source.start_watch.assert_called_with()

    @patch('stretch.source.get_source_classes')
    def test_get_source_map(self, get_source_classes):

        class TestSource(object):
            name = 'source_name'
            def __init__(self, options):
                self.options = options

        get_source_classes.return_value = [TestSource]

        sources = {
            'system': [{
                'source': 'source_name',
                'options': {'foo': 'bar'}
            }]
        }

        source_map = source.get_source_map(sources)
        assert 'system' in source_map
        src = source_map['system'][0]
        assert isinstance(src, TestSource)
        self.assertEquals(src.system_name, 'system')
        self.assertEquals(src.options, {'foo': 'bar'})
