import os
import pyrax
from fabric.api import execute, run, env
from celery.contrib.methods import task

from django.conf import settings
from stretch.salt_api import caller_client
from stretch import utils


class Backend(object):
    def create_host(self, host):
        raise NotImplementedError

    def delete_host(self, host):
        raise NotImplementedError

    def lb_add_host(self, lb, host):
        raise NotImplementedError

    def lb_remove_host(self, lb, host):
        raise NotImplementedError

    def lb_activate_host(self, lb, host):
        raise NotImplementedError

    def lb_deactivate_host(self, lb, host):
        raise NotImplementedError

    def create_lb(self, lb, hosts):
        raise NotImplementedError

    def delete_lb(self, lb):
        raise NotImplementedError


class AutoloadingBackend(Backend):
    def __init__(self):
        super(AutoloadingBackend, self).__init__()


class DockerBackend(AutoloadingBackend):
    def __init__(self, options):
        super(DockerBackend, self).__init__()

    def create_host(self, host):
        self.call_salt('stretch.create_host', host.fqdn)
        return None

    def delete_host(self, host):
        self.call_salt('stretch.delete_host', host.fqdn)

    def lb_add_host(self, lb, host):
        self.call_salt('stretch.lb_add_host', lb.backend_id, host.fqdn)

    def lb_remove_host(self, lb, host):
        self.call_salt('stretch.lb_remove_host', lb.backend_id, host.fqdn)

    def lb_activate_host(self, lb, host):
        self.call_salt('stretch.lb_activate_host', lb.backend_id, host.fqdn)

    def lb_deactivate_host(self, lb, host):
        self.call_salt('stretch.lb_deactivate_host', lb.backend_id, host.fqdn)

    def create_lb(self, lb, hosts):
        self.call_salt('stretch.create_lb', [host.fqdn for host in hosts])
        return lb_id, lb_address
        # TODO: return lb address

    def delete_lb(self, lb):
        self.call_salt('stretch.delete_lb', lb.backend_id)

    def call_salt(self, *args, **kwargs):
        caller_client().function(*args, **kwargs)


class RackspaceBackend(Backend):
    def __init__(self, options):
        super(RackspaceBackend, self).__init__()

        self.username = options.get('username')
        api_key = options.get('api_key')
        self.region = options.get('region').upper()
        self.domainname = options.get('domainname')

        if not settings.SALT_MASTER:
            raise NameError('SALT_MASTER undefined')

        pyrax.set_setting('identity_type', 'rackspace')
        pyrax.set_credentials(self.username, api_key)
        self.cs = pyrax.connect_to_cloudservers(region=self.region)
        self.clb = pyrax.connect_to_cloud_loadbalancers(region=self.region)

        self.image = [img for img in self.cs.images.list()
                      if 'Ubuntu 13.04' in img.name][0]

        self.flavor = [flavor for flavor in self.cs.flavors.list()
                       if flavor.ram == 1024][0]

    def bootstrap_server(self, hostname, domain_name):
        module_dir = os.path.dirname(__file__)
        script = os.path.join(module_dir, 'scripts/bootstrap.sh')

        upload_template(script, '/root/bootstrap.sh', {
            'hostname': hostname,
            'domain_name': domain_name,
            'master': settings.SALT_MASTER
        }, use_jinja=True)

        run('/bin/bash /root/bootstrap.sh')

    def create_host(self, host):
        server = self.cs.servers.create(host.fqdn, self.image.id,
                                        self.flavor.id)
        pyrax.utils.wait_for_build(server, interval=10)

        if server.status != 'ACTIVE':
            raise Exception('failed to create host')

        address = server.networks['private'][0]
        host = 'root@%s' % address
        env.passwords[host] = server.adminPass
        execute(self.bootstrap_server, host.hostname, host.domain_name,
                host=host)

        return address

    def delete_host(self, host):
        for server in self.cs.list():
            if server.name == host.fqdn:
                server.delete()

    def create_lb(self, lb, hosts):
        if not hosts:
            raise Exception('no hosts defined for load balancer')

        vip = self.clb.VirtualIP(type='PUBLIC')
        nodes = [self.get_node(host, lb) for host in hosts]

        lb_obj = self.clb.create(
            str(utils.generate_random_hex(8)),
            port=lb.port,
            protocol=lb.protocol,
            nodes=nodes,
            virtual_ips=[vip],
            algorithm='LEAST_CONNECTIONS'
        )

        pyrax.utils.wait_for_build(lb_obj)

        if lb_obj.status != 'ACTIVE':
            raise Exception('failed to create load balancer')

        return str(lb_obj.id), lb_obj.sourceAddresses['ipv4Public']

    def delete_lb(self, lb):
        self.clb.get(int(lb.backend_id)).delete()

    def lb_add_host(self, lb, host):
        lb_obj = self.clb.get(int(lb.backend_id))
        node = self.get_node(host, lb)
        lb_obj.add_nodes([node])
        pyrax.utils.wait_for_build(lb_obj)

    def lb_remove_host(self, lb, host):
        lb_obj = self.clb.get(int(lb.backend_id))
        try:
            node = [n for n in lb_obj.nodes if n.address == host.address][0]
        except KeyError:
            raise Exception('failed to get node from load balancer')
        node.delete()
        pyrax.utils.wait_for_build(lb_obj)

    def lb_activate_host(self, lb, host):
        lb_obj = self.clb.get(int(lb.backend_id))
        node = [n for n in lb_obj.nodes if n.address == host.address][0]
        node.condition = 'ENABLED'
        node.update()

    def lb_deactivate_host(self, lb, host):
        lb_obj = self.clb.get(int(lb.backend_id))
        node = [n for n in lb_obj.nodes if n.address == host.address][0]
        node.condition = 'DISABLED'
        node.update()

    def get_node(self, host, lb):
        return self.clb.Node(
            address=host.address,
            port=lb.host_port,
            condition='ENABLED'
        )


def get_backend(env):
    return backend_map.get(env.name)


backend_map = {}

for env_name, backends in settings.STRETCH_BACKENDS.iteritems():
    for class_name, options in backends.iteritems():
        # Only one backend per environment
        backend_class = utils.get_class(class_name)
        backend_map[env_name] = backend_class(options)
        break
