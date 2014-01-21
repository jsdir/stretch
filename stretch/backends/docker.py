class DockerBackend(Backend):
    def __init__(self, options):
        super(DockerBackend, self).__init__(options)
        self.autoloads = True

    def create_host(self, host):
        return '127.0.0.1'

    def delete_host(self, host):
        pass

    def lb_add_endpoint(self, lb, host, port):
        LoadBalancer(lb.pk).add_endpoint(host, port)

    def lb_remove_endpoint(self, lb, host, port):
        LoadBalancer(lb.pk).remove_endpoint(host, port)

    def create_lb(self, lb):
        LoadBalancer.create({'id': lb.pk})
        return '127.0.0.1', port

    def delete_lb(self, lb):
        LoadBalancer(lb.pk).delete()

    def call_salt(self, *args, **kwargs):
        caller_client().function(*args, **kwargs)
