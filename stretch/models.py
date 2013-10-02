import os
import shutil
import json
import tarfile
import jsonfield
import uuidfield
from django.db import models
from django_enumfield import enum
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.conf import settings
from celery import current_task, group
from celery.contrib.methods import task
from distutils import dir_util

from stretch import plugins, utils, parser, tasks, signals
from stretch.utils import salt_client
from stretch.sources import Source


class AuditedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        abstract = True


class ChildModel(models.Model):
    parent_content_type = models.ForeignKey(ContentType)
    parent_object_id = models.PositiveIntegerField()
    parent = generic.GenericForeignKey('parent_content_type',
                                       'parent_object_id')

    class Meta:
        abstract = True


class System(models.Model):
    # TODO: alphanumeric (variable name)
    name = models.TextField(unique=True)


class Service(models.Model):
    # TODO: alphanumeric (variable name)
    name = models.TextField(unique=True)
    system = models.ForeignKey(System)
    data = jsonfield.JSONField()


class Release(AuditedModel):
    name = models.TextField()
    sha = models.CharField('SHA', max_length=40)
    system = models.ForeignKey(System)

    def __init__(self, system, source_options):
        self.name = utils.generate_memorable_name()
        self.sha = utils.generate_random_hex(40)
        self.system = system

        # Create from source

        # Create buffers
        buffers = {}
        release_buffer_path = os.path.join(settings.TEMP_DIR, self.sha)
        for name in ('release', 'source'):
            buffer_path = os.path.join(release_buffer_path, name)
            utils.clear_path(buffer_path)
            buffers[name] = buffer_path

        # Acquire lock
        lock = utils.lock('source')
        with lock:
            source = stretch.source
            source.pull(source_options)
            source_path = source.get_path()

            # Copy source into source buffer
            dir_util.copy_tree(source_path, buffers['source'])

            # Create BuildParser
            new_parser = parser.SourceParser(buffers['source'], release, True)

            # Compile and merge release configuration
            source_config = new_parser.get_release_config()

            # Merge to release buffer
            new_parser.copy_to_buffer(buffers['release'])

        # Archive the release
        release_dir = os.path.join(settings.DATA_DIR, 'releases', self.sha)
        utils.makedirs(release_dir)

        # Write release configuration
        with open(os.path.join(release_dir, '%s.json' % self.sha)) as f:
            f.write(json.dumps(source_config))

        # Tar release buffer
        tar_path = os.path.join(release_dir, '%s.tar.gz' % self.sha)
        tar_file = tarfile.open(tar_path, 'w:gz')
        tar_file.add(buffers['release'], '/')
        tar_file.close()

        # Build docker images
        new_parser.build_and_push(self)

        # Clear buffers
        shutil.rmtree(release_buffer_path)

        self.save()

        # Push release to all auto-deploying environments
        for environment in Environment.objects.filter(auto_deploy=True):
            environment.deploy(self)


class Host(ChildModel):
    fqdn = models.TextField(unique=True)
    hostname = models.TextField()
    managed = models.BooleanField()
    groups = generic.GenericRelation(Group)
    instances = generic.GenericRelation(NodeInstance)
    address = models.GenericIPAddressField()

    def add_node(self, node):
        node_instance = NodeInstance(node=node, parent=self)
        self.call_salt('stretch.add_node', node.name)
        node_instance.save()

    def stop_all_nodes(self):
        pass

    def accept_key(self):
        wheel_client.call_func('key.accept', self.fqdn)

    def delete_key(self):
        wheel_client.call_func('key.delete', self.fqdn)

    def sync(self):
        # Install dependencies
        self.call_salt('state.highstate')
        # Synchronize modules
        self.call_salt('saltutil.sync_all')

    def provision(self):
        self.accept_key()
        self.sync()

    def call_salt(self, *args, **kwargs):
        salt_client.cmd(self.fqdn, *args, **kwargs)


class Environment(models.Model):
    name = models.TextField()
    release = models.ForeignKey(Release)
    auto_deploy = models.BooleanField(default=False)
    hosts = generic.GenericRelation(Host)
    groups = generic.GenericRelation(Group)
    system = models.ForeignKey(System)

    unique_together = ('name', 'system')

    def deploy(self, obj):
        if isinstance(obj, Release):
            result = self.deploy_release.delay(release)
            deploy = Deploy(release=release, target=self, task_id=result.id)
            deploy.save()
        elif isinstance(obj, Source):
            self.deploy_source.delay(source)

    def autoload(self, source, existing_parser, new_parser, file_events):
        """
        The files referenced by the existing parser should be considered
        nonexistent. In this context, the existing parser should only be used
        as a reference.
        """
        autoload_nodes = []
        monitored = new_parser.monitored_paths

        def path_contains(path, file_path):
            return not os.path.relpath(file_path, path).startswith('..')

        # Autoload node only if an event took
        # place within the node's monitored path
        for node, paths in monitored:
            for event in file_events:
                path = event.src_path

                if hasattr(event, 'dest_path'):
                    path = event.dest_path

                if any([path_contains(mpath, path) for mpath in paths]):
                    autoload_nodes.append(node)
                    break

        if autoload_nodes:
            # Run build plugins
            new_parser.run_build_plugins(self, autoload_nodes)
            # Run pre-deploy plugins
            new_parser.run_pre_deploy_plugins(self, existing_parser,
                                              autoload_nodes)
            for node in autoload_nodes:
                node_obj = Node.objects.get(name=node.name, system=self.system)

                # Autoloads are done simultaneously because
                # uptime is not that important in development
                for instance in node_obj.instances:
                    instance.autoload(node.app_path)

            # Run post-deploy plugins
            new_parser.run_post_deploy_plugins(self, existing_parser,
                                               autoload_nodes)

    @task
    def deploy_release(self, release):

        total_steps = 8

        def pull_release(release, path, pull_conf=False):
            sha = release.sha
            release_dir = os.path.join(settings.DATA_DIR, 'releases', sha)
            tar_path = os.path.join(release_dir, '%s.tar.gz' % sha)
            tar_file = tarfile.open(tar_path)
            tar_file.extractall(path)
            tar_file.close()

            data = None
            if pull_conf:
                conf_path = os.path.join(release_dir, '%s.json' % sha)
                with open(conf_path) as conf_file:
                    data = json.loads(conf_file.read())

            return data

        def update_status(current, description):
            current_task.update_state(state='PROGRESS',
                meta={
                    'description': description,
                    'current': current,
                    'total': total_steps
                }
            )

        existing_release = self.release
        new_release = release

        # Pull release
        update_status(1, 'Pulling release')

        # Create environment buffers
        buffers = {}
        env_buffer_path = os.path.join(settings.TEMP_DIR,
                                       'systems',
                                       self.system.name,
                                       self.name)

        # Setup existing release buffer
        buffers['existing'] = os.path.join(env_buffer_path, 'existing')
        utils.makedirs(buffers['existing'])
        if existing_release and not os.listdir(buffers['existing']):
            # Pull existing release
            pull_release(existing_release, buffers['existing'])

        # Setup new release buffer
        buffers['new'] = os.path.join(env_buffer_path, 'new')
        utils.clear_path(buffers['new'])

        # Pull new release
        release_config_data = pull_release(new_release, buffers['new'], True)

        # Parse sources
        new_parser = parser.SourceParser(buffers['new'], new_release)
        existing_parser = None
        if existing_release:
            existing_parser = parser.SourceParser(buffers['existing'],
                                                  existing_release)

        # Run build plugins
        update_status(2, 'Running build plugins')
        new_parser.run_build_plugins(self)

        # Run pre-deploy plugins
        update_status(3, 'Running pre-deploy plugins')
        new_parser.run_pre_deploy_plugins(self, existing_parser)

        # Parse release configuration
        update_status(4, 'Parsing release configuration')
        release_config = self.get_release_config(
            new_parser, new_release, existing_release)

        # Push images and configurations to nodes
        update_status(5, 'Pushing images and configurations to nodes')
        hosts, instances = self.group_instances()

        # Mount templates
        templates_path, local_path = self.mount_templates(new_parser)

        # Pull release
        fqdns = [host.fqdn for host in hosts.keys()]
        list(salt_client.cmd_batch(fqdns, 'stretch.pull', [{
            'release_sha': new_release.sha,
            'release_name': new_release.name,
            'registry_url': settings.REGISTRY_URL,
            # TODO: is template_path even needed when using pks?
            # 'template_path': local_path,
            'config': release_config
        }], batch=str(settings.BATCH_SIZE), expr_form='list'))

        # Unmount templates
        self.unmount_templates(templates_path)

        # Deploy to nodes
        update_status(6, 'Deploying to nodes')

        # TODO: have this run in batch size
        for instance, fqdn in instances:
            instance.deactivate()
            salt_client.cmd(fqdn, 'stretch.deploy', [instance.pk, new_release.sha])
            instance.activate()

        # Switch buffers
        update_status(7, 'Switching buffers')

        # Clear existing buffer
        utils.clear_path(buffers['existing'])
        dir_util.copy_tree(buffers['new'], buffers['existing'])
        utils.clear_path(buffers['new'])

        # Run post-deploy plugins
        update_status(8, 'Running post-deploy plugins')
        new_parser.run_post_deploy_plugins(self, existing_parser)

    @task
    def deploy_source(self, source):
        new_parser = source.parser

        # Build images
        new_parser.build_local()
        new_parser.run_build_plugins(self)
        new_parser.run_pre_deploy_plugins(self, None)

        # Parse release configuration
        release_config = self.get_release_config(new_parser, None, None)

        # Push images and configurations to nodes
        hosts, instances = self.group_instances()
        templates_path, local_path = self.mount_templates(new_parser)

        fqdns = [host.fqdn for host in hosts.keys()]
        list(salt_client.cmd_batch(fqdns, 'stretch.autoload_deploy', [{
            # TODO: is template_path even needed when using pks?
            # 'template_path': local_path,
            'config': release_config
        }], batch=str(settings.BATCH_SIZE), expr_form='list'))

        # Unmount templates
        self.unmount_templates(templates_path)

        # Run post-deploy plugins
        new_parser.run_post_deploy_plugins(self, None)

    def group_instances(self):
        hosts = {}
        instances = []

        for instance in NodeInstance.objects.filter(environment=self):
            host, node_pk = instance.get_host(), str(instance.node.pk)
            instances.append((instance, host.fqdn))
            if hosts.has_key(host):
                if node_pk not in hosts[host]:
                    hosts[host].append(node_pk)
            else:
                hosts[host] = [node_pk]

        return hosts, instances

    def mount_templates(self, parser):
        local_path = '%s/%s' % (self.system.pk, self.pk)
        templates_path = os.path.join(settings.CACHE_DIR, 'templates',
                                      local_path)

        utils.clear_path(templates_path)
        parser.mount_templates(templates_path)

        return templates_path, local_path

    def unmount_templates(self, path):
        shutil.rmtree(path)

    def get_release_config(parser, new_release, existing_release):
        # Parse release configuration
        release_config_data = parser.get_release_config()
        node_configs = parser.parse_release_config(
            release_config_data, self, new_release, existing_release)

        # Release node names with pks
        release_config = {}
        for node_name, node_config in node_configs.iteritems():
            node_pk = str(Node.objects.get(name=node_name).pk)
            release_config[node_pk] = node_name

        return release_config

    def add_host(self, node):
        host = backend.create_host()
        host.parent = self
        host.save()
        return host

    def add_unmanaged_host(self, node, fqdn, hostname, address):
        host = Host(hostname=hostname, fqdn=fqdn, managed=False,
                    address=address)
        host.provision()
        host.parent = self
        host.save()
        return host


class Node(models.Model):
    name = models.TextField()
    system = models.ForeignKey(System)

    unique_together = ('name', 'system')


class NodeInstance(ChildModel):
    id = uuidfield.UUIDField(auto=True, primary_key=True)
    node = models.ForeignKey(Node)
    environment = models.ForeignKey(Environment)

    def autoload(self, app_path):
        self.get_host().call_salt('stretch.autoload', self.pk, app_path)

    def get_host(self):
        if isinstance(self.parent, Host):
            return self.parent
        else:
            return self.parent.parent

    def activate(self):
        pass

    def deactivate(self):
        pass


class PortBinding(model.Model):
    instance = models.ForeignKey(NodeInstance)
    source = models.IntegerField()
    destination = models.IntegerField()


class LoadBalancer(models.Model):
    port = models.IntegerField()
    host_port = models.IntegerField()
    protocol = models.TextField()
    ip = models.GenericIPAddressField()
    backend_id = models.CharField(max_length=32, unique=True)

    @classmethod
    def create(cls, port, host_port, protocol, hosts):
        lb = cls(port=port, host_port=host_port, protocol=protocol)
        lb.backend_id, lb.ip = stretch.backend.create_lb(self, hosts)
        return lb

    def add_host(self, host):
        stretch.backend.add_to_lb(self.backend_id, host)

    def remove_host(self, host):
        stretch.backend.remove_from_lb(self.backend_id, host)

    def delete(self):
        stretch.backend.delete_lb(self.backend_id)
        super(LoadBalancer, self).delete()


class Group(ChildModel):
    name = models.TextField(unique=True)
    environment = models.ForeignKey(Environment)
    minimum_nodes = models.IntegerField(default=1)
    maximum_nodes = models.IntegerField(default=None)
    node = models.ForeignKey(Node)
    hosts = generic.GenericRelation(Host)
    instances = generic.GenericRelation(NodeInstance)
    load_balancer = models.OneToOneField(LoadBalancer)

    unique_together = ('name', 'environment')

    def is_node_group(self):
        return isinstance(self.parent, Host)

    def scale_up(self, amount):
        if self.is_node_group():
            pass # TODO: node scaling
        else:
            self.check_valid_amount(self.host_count + amount)
            group(tasks.create_host.s(self) for _ in xrange(amount))().get()

            self.environment.update_configuration()

    def scale_down(self, amount):
        if self.is_node_group():
            pass # TODO: node scaling
        else:
            self.check_valid_amount(self.host_count - amount)

            hosts = self.hosts[0:amount]

            for host in hosts:
                host.parent = None
                host.save()

            self.environment.update_configuration()
            group(tasks.remove_host.s(host, self) for host in hosts)().get()

    def add_load_balancer(self, port, host_port, protocol):
        if self.is_node_group():
            pass # TODO: node scaling
        else:
            if not self.load_balancer and self.hosts:
                self.load_balancer = LoadBalancer.create(port, host_port,
                                                         protocol, self.hosts)

    def scale_to(self, amount):
        relative_amount = amount - self.host_count
        if relative_amount > 0:
            self.scale_up(relative_amount)
        elif relative_amount < 0:
            self.scale_down(-relative_amount)

    def check_valid_amount(self, amount):
        if self.maximum_nodes == None:
            valid = amount >= self.minimum_nodes
        else:
            valid = self.minimum_nodes <= amount <= self.maximum_nodes
        if not valid:
            raise Exception('Invalid scaling amount')

    @property
    def host_count(self):
        return self.hosts.count()

"""
class Trigger(models.Model):
    environment = models.ForeignKey(Environment)


class Action(models.Model):
    trigger = models.OneToOneField(Trigger)
    module, function


class Event(models.Model):
    trigger = models.OneToOneField(Trigger)
    module, function "monitoring"

"""
class Metric(models.Model):
    environment = models.ForeignKey(Environment)


class Deploy(models.Model):
    release = models.ForeignKey(Release)
    target = models.ForeignKey(Environment)
    task_id = models.CharField(max_length=128)


@receiver(signals.source_changed)
def on_source_changed(sender, file_events):
    for environment in Environment.objects.filter(auto_deploy=True):
        environment.autoload(
            sender, sender.existing_parser, sender.parser, file_events)
