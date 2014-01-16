from twisted.internet import reactor, threads
from twisted.python import log
from twisted.web import server

#from stretch.agent.task_server import TaskServer, task
# No casting to strings in the agent


class Agent(object):
    @exportRpc
    def add_node(self, node_id):
        objects.Node.create({'id': node_id})
        return deferred.success()

    @exportRpc
    def remove_node(self, node_id):
        objects.Node(node_id).delete()
        # what about errors, see how autobahn handles this
        return deferred.success()

    @exportRpc
    def pull_node(self, node_id, options):
        return threads.deferToThread(objects.Node(node_id).pull, options)

    @exportRpc
    def add_instance(self, instance_id, node_id, host_name, config_key):
        return threads.deferToThread(objects.Instance.create, {
            'id': instance_id,
            'node_id': node_id,
            'host_name': host_name,
            'config_key': config_key
        })

    @exportRpc
    def remove_instance(self, instance_id):
        # Must be async because the instance has to gracefully stop
        return threads.deferToThread(objects.Instance(instance_id).delete)

    @exportRpc
    def reload_instance(self, instance_id):
        return threads.deferToThread(objects.Instance(instance_id).reload)

    @exportRpc
    def restart_instance(self, instance_id):
        return threads.deferToThread(objects.Instance(instance_id).restart)

    @exportRpc
    def add_lb(self, lb_id):
        return threads.deferToThread(objects.LoadBalancer(lb_id).create,
            {'id': lb_id})

    @exportRpc
    def remove_lb(self, lb_id):
        return threads.deferToThread(objects.LoadBalancer(lb_id).delete)

    @exportRpc
    def add_endpoint(self, lb_id, endpoint):
        return threads.deferToThread(objects.LoadBalancer(lb_id).add_endpoint,
            endpoint)

    @exportRpc
    def remove_endpoint(self, lb_id, endpoint):
        return threads.deferToThread(
            objects.LoadBalancer(lb_id).remove_endpoint, endpoint)
