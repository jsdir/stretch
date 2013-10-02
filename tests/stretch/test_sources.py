from mock import Mock, patch, call
from nose.tools import eq_, raises
import time

from stretch import sources


class TestFileSystemSource(object):
    @patch('stretch.sources.FileSystemSource.parse')
    def test_event_handling(self, parse):
        source = sources.FileSystemSource({'path': 'foo'})
        source.on_files_change = Mock()

        handler = sources.EventHandler(source)
        timeout = handler.timeout = 0.1

        handler.on_any_event(1)
        time.sleep(0.05)
        handler.on_any_event(2)
        time.sleep(0.15)
        handler.on_any_event(1)
        time.sleep(0.15)

        eq_(source.on_files_change.mock_calls, [call([1, 2]), call([1])])

    @patch('stretch.sources.FileSystemSource.parse')
    def test_get_path(self, parse):
        source = sources.FileSystemSource({'path': 'foo'})
        eq_(source.get_path(), 'foo')

    @raises(NameError)
    def test_fails_without_path(self):
        source = sources.FileSystemSource({})


class TestGitRepositorySource(object):
    @patch('stretch.sources.GitRepositorySource.pull')
    def test_get_path(self, pull):
        source = sources.GitRepositorySource({
            'ref': '00000000',
            'url': 'url'
        })
        source.get_path()
        assert pull.was_called

    @raises(NameError)
    def test_fails_without_url(self):
        source = sources.GitRepositorySource({'ref': '00000000'})


class TestSource(object):
    @patch('stretch.sources.SourceParser')
    def test_parser_change(self, source_parser):
        source = sources.Source({})
        eq_(source.parser, None)
        parser = source.parse()
        source.parse()
        eq_(parser, source.existing_parser)


class TestAutoloadableSource(object):
    def test_autoload_is_default(self):
        source = sources.AutoloadableSource({})
        eq_(source.autoload, True)

    @raises(Exception)
    def test_monitor_fails_without_autoload(self):
        source = sources.AutoloadableSource({'autoload': False})
        source.do_monitor = Mock()
        source.monitor()
        assert not source.do_monitor.called

    def test_monitor_runs_with_autoload(self):
        source = sources.AutoloadableSource({'autoload': True})
        source.do_monitor = Mock()
        source.monitor()
        assert source.do_monitor.was_called
