import logging
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from stretch.source import LiveSource


log = logging.getLogger(__name__)


class EventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super(EventHandler, self).__init__()
        self.callback = callback

    def on_any_event(self, event):
        path = event.src_path
        if hasattr(event, 'dest_path'):
            path = event.dest_path
        self.callback(path)


class FileSystemSource(LiveSource):

    name = 'filesystem'

    def __init__(self, options):
        super(FileSystemSource, self).__init__(options)
        self.path = self.require_option('path')

    def watch(self):
        log.info('Monitoring %s' % self.path)
        observer = Observer()
        observer.schedule(EventHandler(self.on_file_change), self.path,
                          recursive=True)
        observer.start()

    def pull(self, options):
        return self.path
