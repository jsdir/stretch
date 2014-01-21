class EventHandler(FileSystemEventHandler):
    def __init__(self, callback):
        super(EventHandler, self).__init__()
        self.callback = callback
        self.queue = []
        self.timeout = 0.2
        self.timer = None

    def on_any_event(self, event):
        self.queue.append(event)
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(self.timeout, self.push_queue)
        self.timer.start()

    def push_queue(self):
        self.callback(self.queue)
        self.queue = []


class FileSystemSource(AutoloadableSource):
    def __init__(self, options):
        super(FileSystemSource, self).__init__(options)
        self.path = self.require_option('path')

    def do_watch(self):
        log.info('Monitoring %s' % self.path)
        observer = Observer()
        observer.schedule(EventHandler(self.on_change), self.path,
                          recursive=True)
        observer.start()

    def on_change(self, events):
        # Autoload node only if an event took place within the node's
        # monitored path
        snapshot = parser.Snapshot(self.pull())
        autoload_nodes = []

        for node, paths in snapshot.monitored_paths.iteritems():
            for event in events:
                path = event.src_path

                if hasattr(event, 'dest_path'):
                    path = event.dest_path

                if any([utils.path_contains(mpath, path) for mpath in paths]):
                    autoload_nodes.append(node)
                    break

        if autoload_nodes:
            signals.sync_source.send(sender=self, nodes=autoload_nodes)

    def pull(self, options={}):
        return self.path
