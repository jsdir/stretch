import pymongo
import docker

from twisted.internet import task
from autobahn.twisted.websocket import listenWS
from autobahn.wamp import exportRpc, WampServerFactory, WampServerProtocol


CONFIG_TTL = 10 # seconds before an instance's config key expires
PORT = 8090
db_client = pymongo.MongoClient()


class Agent(object):

    def __init__(self, db):
        self.db = db_client[db]

    @exportRpc
    def add_node(self, node_id):
        self.db['nodes'].insert({'_id': node_id})

    @exportRpc
    def remove_node(self, node_id):
        self.db['nodes'].remove({'_id': node_id})

    @exportRpc
    @defer.inlineCallbacks
    def pull_node(self, node_id, options):
        # Pull image
        # should only talk with db not docker
        if not options['app_path']:
            yield threads.deferToThread(self.docker.pull,
                                        [options['image'], options['sha']])


        # Prepare to pull templates
        templates_path = self.get_templates_path()
        src = 'salt://templates/%s/%s' % (args['env_id'], self.data['_id'])

        # Remove all contents before adding new templates
        utils.clear_path(templates_path)

        # Pull templates
        caller_client().function('cp.get_dir', src, templates_path)

        node.update(args)

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
        return threads.deferToThread(objects.Instance(instance_id).delete)

    @exportRpc
    def reload_instance(self, instance_id):
        return threads.deferToThread(objects.Instance(instance_id).reload)

    @exportRpc
    def restart_instance(self, instance_id):
        # remove cid from database before restart so the supervisor doesn't think it crashed
        return threads.deferToThread(objects.Instance(instance_id).restart)


class AgentServerProtocol(WampServerProtocol):

    def __init__(self, agent):
        self.agent = agent

    def onSessionOpen(self):
        self.registerForRpc(self.agent, 'ns#')


class InstanceSupervisor(object):

    def __init__(self, db, docker):
        self.db = db
        self.docker = docker

    def start(self, ttl):
        # Make the interval smaller than the key ttl to make up for the
        # extra time it takes to collect and process the running instances.
        interval = ttl / 2.0
        task.LoopingCall(self.check_instances).start(CONFIG_TTL / 2.0)

    @staticmethod
    def check_instances():
        # Get the ids of all running containers.
        cids = [container['Id'] for container in self.docker.containers()]

        # Get ids of containers that should be running
        for instance in self.db['instances']:
            if instance['cid'] not in cids:
                # Either the host restarted or the container stopped unnaturally;
                # restart it and assign new cid
                self.db.update( {'cid': self.start_instance(instance)})
            # Set on etcd

        # Only test this and submethods

    def start_instance(self):
        return self.docker.start(container, binds={
            ''
        }, ports=[])

    def remove_isntance(self):
        pass

    def reload_instance(self):
        pass

    def restart_instance(self):
        pass


def get_option(short_name, long_name=None):
    return None


if __name__ == '__main__':
    # Load services
    db = client["stretch-agent"]
    docker_client = docker.Client(base_url='unix://var/run/docker.sock',
        version='1.6', timeout=10)

    # Start supervsior
    supervisor = InstanceSupervisor(db, docker_client)
    supervisor.start(get_option('t', 'ttl') or CONFIG_TTL)

    # Start agent
    agent = Agent(db, supervisor)
    port = get_option('p', 'port') or PORT
    factory = WampServerFactory('ws://localhost:%s' % port, debugWamp=True)
    factory.protocol = AgentServerProtocol
    listenWS(factory)

    reactor.run()
