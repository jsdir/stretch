from twisted.web import xmlrpc, server
from twisted.internet import reactor, defer
from twisted.internet.protocol import Factory
from twisted.protocols.portforward import ProxyServer, ProxyFactory
from twisted.application import internet, service


class TCPLoadBalancerFactory(Factory):
    endpoints = {}

    def buildProtocol(self, addr):
        factory = self.endpoints.pop(0, None) or ProxyFactory(None, None)
        self.endpoints.append(factory)
        return factory.buildProtocol(addr)

    def addEndpoint(self, endpoint):
        endpoint = tuple(endpoint)
        if endpoint not in self.endpoints:
            host, port = endpoint
            self.endpoints[endpoint] = ProxyFactory(host, port)
        else:
            raise ObjectExists('endpoint already exists in load balancer')

    def removeEndpoint(self, endpoint):
        endpoint = tuple(endpoint)
        try:
            self.endpoints.pop(endpoint)
        except KeyError:
            raise ObjectDoesNotExist('endpoint does not exist in load '
                                     'balancer')


class TCPLoadBalancerServer(xmlrpc.XMLRPC):
    load_balancers = {}

    def xmlrpc_start_lb(self, lb_id):
        if lb_id in self.load_balancers:
            raise LoadBalancerException('load balancer with id "%s" is already '
                                        'running' % lb_id)
        factory = TCPLoadBalancerFactory()
        port = reactor.listenTCP(0, factory)
        self.load_balancers[lb_id] = dict(port=port, factory=factory)
        return port.getHost().port

    def xmlrpc_add_endpoint(self, lb_id, endpoint):
        self.get_lb(lb_id)['factory'].addEndpoint(endpoint)
        return True

    def xmlrpc_remove_endpoint(self, lb_id, endpoint):
        self.get_lb(lb_id)['factory'].removeEndpoint(endpoint)
        return True

    def xmlrpc_stop_lb(self, lb_id):
        lb = self.get_lb(lb_id)
        defer.maybeDeferred(lb['port'].stopListening)
        return True

    def get_lb(self, lb_id):
        try:
            return self.load_balancers[lb_id]
        except KeyError:
            raise ObjectDoesNotExist('load balancer with id "%s" does not '
                                     'exist' % lb_id)


class LoadBalancerException(Exception):
    pass


class ObjectDoesNotExist(LoadBalancerException):
    pass


class ObjectExists(LoadBalancerException):
    pass


def run():
    s = TCPLoadBalancerServer()
    # TODO: use UNIX sockets
    # reactor.listenUNIX('/var/run/stretch-agent/lb.sock', server.Site(s))
    reactor.listenTCP(24226, server.Site(s))
    reactor.run()
