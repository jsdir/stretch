import os
import pyrax
from fabric.api import execute, run, env
from celery.contrib.methods import task

from django.conf import settings
from stretch.utils import wheel_client
from stretch.api import models
from stretch import utils


class Backend(object):
    def create_host(self):
        raise NotImplementedError

    def delete_host(self, host):
        raise NotImplementedError

    def add_to_lb(self, lb_id, host):
        raise NotImplementedError

    def remove_from_lb(self, lb_id, host):
        raise NotImplementedError

    def create_lb(self, port):
        raise NotImplementedError


class AutoloadingBackend(Backend):
    def load(self, existing_parser, new_parser, changed_files):
        raise NotImplementedError


class DockerBackend(AutoloadingBackend):
    def __init__(self):
        super(DockerBackend, self).__init__()
        # All hosts in the docker backend are unmanaged.
        self.host_exception = Exception(
            'DockerBackend only uses unmanaged hosts.')

    def create_host(self):
        raise self.host_exception

    def delete_host(self, host):
        raise self.host_exception

    # TODO: full implementation


class RackspaceBackend(Backend):
    def __init__(self, options):
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

    def create_host(self):
        hostname = 'node-%s' % utils.generate_random_hex(8)
        server = self.cs.servers.create(hostname, self.image.id,
                                        self.flavor.id)
        pyrax.utils.wait_for_build(server, interval=10)

        if server.status != 'ACTIVE':
            raise Exception('Failed to create host')

        domain_name = settings.DOMAIN_NAME
        if domain_name:
            fqdn = '%s.%s' % (hostname, domain_name)
        else:
            fqdn = hostname

        ip = server.networks['private'][0]
        host = 'root@%s' % ip
        env.passwords[host] = server.adminPass
        execute(self.bootstrap_server, hostname, domain_name, host=host)

        host = models.Host(hostname=hostname, fqdn=fqdn, managed=True,
                           address=ip)

        host.provision()
        host.save()

        return host

    def delete_host(self, host):
        if host.managed:
            wheel_client.call_func('key.delete', host.fqdn)
            salt_client.cmd(host.fqdn, 'stretch.delete')
            for server in self.cs.list():
                if server.name == host.hostname:
                    server.delete()

    def create_lb(self, lb_object, hosts):
        if not hosts:
            raise Exception('No hosts defined for load balancer')

        vip = clb.VirtualIP(type='PUBLIC')
        nodes = [self.get_node(host, lb_object) for host in hosts]

        lb = self.clb.create(
            str(utils.generate_random_hex(16)),
            port=host_port.port,
            protocol=host_port.protocol,
            nodes=nodes,
            virtual_ips=[vip],
            algorithm='LEAST_CONNECTIONS'
        )

        pyrax.utils.wait_for_build(lb)

        if lb.status != 'ACTIVE':
            raise Exception('Failed to create load balancer')

        lb.update(algorithm='LEAST_CONNECTIONS')
        return str(lb.id), lb.sourceAddresses['ipv4Public']

    def delete_lb(self, lb_object):
        lb = clb.get(int(lb_object.backend_id))
        lb.delete()

    def add_to_lb(self, lb_object, host):
        lb = clb.get(int(lb_object.backend_id))
        node = self.get_node(host, lb_object)
        lb.add_nodes([node])
        pyrax.utils.wait_for_build(lb)

    def remove_from_lb(self, lb_object, host):
        lb = clb.get(int(lb_object.backend_id))
        try:
            node = [n for n in lb.nodes if n.address == host.address][0]
        except KeyError:
            raise Exception('Failed to get node from load balancer')
        node.delete()
        pyrax.utils.wait_for_build(lb)

    def get_node(self, host, lb_object):
        return self.clb.Node(
            address=host.address,
            port=lb_object.host_port,
            condition='ENABLED'
        )

    # TODO: full implementation


def get_backend(env):
    return backend_map.get(env.name)


backend_map = {}

for env_name, backends in settings.STRETCH_BACKENDS.iteritems():
    for class_name, options in backends.iteritems():
        # Only one backend per environment
        backend_class = utils.get_class(class_name)
        backend_map[env_name] = source_class(options)
        break
