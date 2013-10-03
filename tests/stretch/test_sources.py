from mock import Mock, patch, call
from nose.tools import eq_, raises
import time

from stretch import sources


class TestSource(object):
    @raises(NameError)
    def test_require_option(self):
        source = sources.Source({'foo': 'bar'})
        eq_(source.require_option('foo'), 'bar')
        option = source.require_option('what')


class TestAutoloadableSource(object):
    def test_autoload_is_default(self):
        source = sources.AutoloadableSource({})
        eq_(source.autoload, True)

    def test_watch_fails_without_autoload(self):
        source = sources.AutoloadableSource({'autoload': False})
        source.do_watch = Mock()
        source.watch()
        assert not source.do_watch.called

    def test_watch_runs_with_autoload(self):
        source = sources.AutoloadableSource({'autoload': True})
        source.do_watch = Mock()
        source.watch()
        assert source.do_watch.was_called


class TestFileSystemSource(object):
    def test_event_handler(self):
        callback = Mock()
        handler = sources.EventHandler(callback)
        timeout = handler.timeout = 0.1

        handler.on_any_event(1)
        time.sleep(0.05)
        handler.on_any_event(2)
        time.sleep(0.15)
        handler.on_any_event(1)
        time.sleep(0.15)

        eq_(callback.mock_calls, [call([1, 2]), call([1])])
