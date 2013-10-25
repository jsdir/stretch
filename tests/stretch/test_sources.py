from mock import Mock, patch, call
from nose.tools import eq_, raises
import time

from stretch import sources, signals


class TestSource(object):
    @raises(NameError)
    def test_require_option(self):
        source = sources.Source({'foo': 'bar'})
        eq_(source.require_option('foo'), 'bar')
        source.require_option('what')


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
    @patch('stretch.parser.Snapshot.__new__')
    @patch('watchdog.observers.Observer.__new__')
    def test_source(self, observer, snapshot_new):
        signals.sync_source.send = Mock()
        snapshot = Mock()
        snapshot.monitored_paths = {
            'node1': ['foo'],
            'node2': ['bar'],
            'node3': ['foobar']
        }

        snapshot_new.return_value = snapshot

        source = sources.FileSystemSource({'path': 'foo'})
        source.do_watch()
        source.on_change([
            Mock(spec=['src_path'], src_path='foo'),
            Mock(spec=['src_path', 'dest_path'], src_path='bar',
                 dest_path='foobar')
        ])
        signals.sync_source.send.assert_called_with(sender=source,
                                                    nodes=['node1', 'node3'])
        signals.sync_source.send.reset_mock()

        snapshot.monitored_paths = {}
        source.on_change([
            Mock(spec=['src_path'], src_path='foo'),
            Mock(spec=['src_path', 'dest_path'], src_path='bar',
                 dest_path='foobar')
        ])
        assert not signals.sync_source.send.called


class TestGitRepositorySource(object):
    @patch('django.conf.settings.STRETCH_CACHE_DIR', '/cache')
    @patch('stretch.utils.makedirs', Mock())
    @patch('stretch.sources.git')
    def test_pull(self, git):
        source = sources.GitRepositorySource({'url': 'repo_url'})
        path = '/cache/046e9fb39a04020f6cabc0a83e01ad3c108a6225'

        with patch('os.path.exists', return_value=False):
            # assert latest commit pulled
            eq_(source.pull(), path)
            git.Repo.clone_from.assert_called_with('repo_url', path)

        git.reset_mock()
        with patch('os.path.exists', return_value=True):
            eq_(source.pull(), path)
            git.Repo.assert_called_with(path)

        eq_(source.pull({'ref': 'a'}), path)
        git.reset_mock()
        eq_(source.pull({'ref': 'a'}), path)
        # assert repo 'a' cached
        assert not git.Repo.called
        assert not git.Repo.clone_from.called



class TestEventHandler(object):
    def test_event_handler(self):
        callback = Mock()
        handler = sources.EventHandler(callback)
        handler.timeout = 0.02

        handler.on_any_event(1)
        time.sleep(0.01)
        handler.on_any_event(2)
        time.sleep(0.03)
        handler.on_any_event(1)
        time.sleep(0.03)

        eq_(callback.mock_calls, [call([1, 2]), call([1])])


class TestSourceMap(object):
    @patch('stretch.sources.get_source_map')
    def test_get_sources(self, get_source_map):
        get_source_map.return_value = {'system': ['foo']}
        system = Mock()
        system.name = 'system'
        eq_(sources.get_sources(system), ['foo'])
        system = Mock()
        system.name = 'bar'
        eq_(sources.get_sources(system), [])

    @patch('stretch.sources.get_source_map')
    def test_get_system(self, get_source_map):
        get_source_map.return_value = {'system': ['foo']}
        eq_(sources.get_system('foo'), 'system')
        eq_(sources.get_system('bar'), None)

    @patch('stretch.sources.get_source_map')
    def test_watch(self, get_source_map):
        source = Mock(spec=[])
        autoloadable_source = Mock(spec=['watch'])
        get_source_map.return_value = {'system': [source, autoloadable_source]}
        sources.watch()
        autoloadable_source.watch.assert_called_with()

    @patch('stretch.utils.get_class')
    def test_get_source_map(self, get_class):

        class TestSource(object):
            def __init__(self, options):
                self.options = options

        get_class.return_value = TestSource

        source_dict = {
            'system': {
                'path.to.SourceClass': {
                    'foo': 'bar',
                }
            }
        }

        source_map = sources.get_source_map(source_dict)
        assert 'system' in source_map
        assert isinstance(source_map['system'][0], TestSource)
        eq_(source_map['system'][0].options, {'foo': 'bar'})
