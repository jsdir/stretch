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


class TestEventHandler(object):
    def test_event_handler(self):
        callback = Mock()
        handler = source.EventHandler(callback)
        handler.timeout = 0.02

        handler.on_any_event(1)
        time.sleep(0.01)
        handler.on_any_event(2)
        time.sleep(0.03)
        handler.on_any_event(1)
        time.sleep(0.03)

        eq_(callback.mock_calls, [call([1, 2]), call([1])])