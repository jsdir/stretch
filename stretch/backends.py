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

    @task()
    def create_host_with_node(self, node):
        host = self.create_host()
        host.add_node(node)
        return host


class AutoloadingBackend(Backend):
    def load(self, existing_parser, new_parser, changed_files):
        raise NotImplementedError


class DockerBackend(AutoloadingBackend):
    def __init__(self):
        super(DockerBackend, self).__init__()

    def load_source(self, source):
        parser = source.parse()

    def create_host(self):
        # Communicate with locally installed agent
        pass

    def delete_host(self, host):
        # Communicate with locally installed agent
        pass


class RackspaceBackend(Backend):
    def __init__(self, options):
        self.username = options.get('username')
        api_key = options.get('api_key')
        self.region = options.get('region')
        self.domainname = options.get('domainname')

        if not settings.SALT_MASTER:
            raise NameError('SALT_MASTER undefined')

        pyrax.set_setting('identity_type', 'rackspace')
        pyrax.set_credentials(self.username, api_key)
        self.cs = pyrax.connect_to_cloudservers(region=self.region)

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
