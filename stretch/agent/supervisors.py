"""
Services to ensure that all instances and load balancers are running and
discoverable.
"""
import xmlrpclib
from twisted.web import xmlrpc, server
from twisted.internet import reactor, defer, task
from twisted.internet.protocol import Factory
from twisted.protocols.portforward import ProxyServer, ProxyFactory
from twisted.application import internet, service
from treq import get, post

from stretch import utils, models
#from stretch.agent.instances import Instance


LB_SUPERVISOR_PORT = 24226
ENDPOINT_SUPERVISOR_PORT = 24227


class TCPLoadBalancerFactory(Factory):
    endpoints = {}

    def buildProtocol(self, addr):
        factory = self.endpoints.pop(0, None) or ProxyFactory(None, None)
        self.endpoints['a'] = factory
        return factory.buildProtocol(addr)

    def add_endpoint(self, host, port):
        endpoint = tuple(host, port)
        if endpoint not in self.endpoints:
            self.endpoints[endpoint] = ProxyFactory(host, port)
        else:
            raise ObjectExists('endpoint already exists in load balancer')

    def remove_endpoint(self, endpoint):
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

    def xmlrpc_add_endpoint(self, lb_id, host, port):
        self.get_lb(lb_id)['factory'].add_endpoint(host, port)
        return True

    def xmlrpc_remove_endpoint(self, lb_id, host, port):
        self.get_lb(lb_id)['factory'].remove_endpoint(host, port)
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


def run_lb_supervisor():
    # Load loadbalancers from ORM
    # Set new persistent endpoints
    s = TCPLoadBalancerServer()
    reactor.listenTCP(LB_SUPERVISOR_PORT, server.Site(s))
    reactor.run()


@utils.memoized
def lb_supervisor_client():
    return xmlrpclib.ServerProxy('http://127.0.0.1:%s/' % LB_SUPERVISOR_PORT)


# If the instance's node hasn't been pushed to its host or if
# the environment has no release set, the instance should wait, make this a
# lot more readable


class EndpointSupervisor(xmlrpc.XMLRPC):
    groups = []

    def __init__(self, groups):
        xmlrpc.XMLRPC.__init__(self)
        [self.xmlrpc_add_group(group.pk, group.config_key) for group in groups]

    def xmlrpc_add_group(self, group_id, config_key):
        if group_id not in self.groups:
            self.groups.append(group_id)
            self.watch(group_id, config_key)
        return True

    def xmlrpc_remove_group(self, group_id):
        self.groups.remove(group_id)
        return True

    def watch(self, group_id, config_key, index=None):

        def handle_response(response):
            response.addCallback(key_changed)

        def key_changed(result):
            if group_id in self.groups:
                key = result['key'].lstrip(config_key)
                if key != 'lb':
                    if result.get('newKey'):
                        # add endpoint
                        endpoint = json.loads(result['value'])
                        self.add_endpoint(group_id, endpoint)
                    elif result['action'] == 'DELETE':
                        # remove endpoint
                        endpoint = json.loads(result['prevValue'])
                        self.remove_endpoint(group_id, endpoint)

                self.watch(group_id, config_key, result['index'])

        url = 'http://127.0.0.1:4001/v1/watch%s' % config_key
        if index:
            r = post(url, data={'index': index})
        else:
            r = get(url)

        r.addCallback(handle_response)
        return True

    def add_endpoint(group_id, endpoint):
        group = models.Group.objects.get(pk=group_id)
        group.load_balancer.add_endpoint(endpoint)

    def remove_endpoint(group_id, endpoint):
        group = models.Group.objects.get(pk=group_id)
        group.load_balancer.remove_endpoint(endpoint)


def run_endpoint_supervisor():
    """
    Listens for changes over etcd and adds/removes endpoints where necessary
    # Gets populated with all loadbalancers from all services and listens for
    # create/remove hooks,
    """
    # Load all groups that use a load balancer
    groups = [lb.group for lb in models.LoadBalancer.objects.all()]
    reactor.listenTCP(ENDPOINT_SUPERVISOR_PORT,
                      server.Site(EndpointSupervisor(groups)))
    reactor.run()


@utils.memoized
def endpoint_supervisor_client():
    return xmlrpclib.ServerProxy('http://127.0.0.1:%s/' %
                                 ENDPOINT_SUPERVISOR_PORT)


def check_instances():
    cids = utils.run_cmd(['docker', 'ps', '-q'])[0].splitlines()
    for instance in Instance.get_instances():
        cid = instance.data['cid']
        if cid in cids:
            # Instance is running
            # Set endpoint key
            instance.set_endpoint()
        else:
            # Instance is down
            instance.data['cid'] = None
            instance.data['endpoint'] = None
            instance.save()
            # Log the event and start the instance
            instance.start()


def run_instance_supervisor():
    t = task.LoopingCall(check_instances)
    t.start(10.0)
    reactor.run()