import os
import shutils
import json
import tarfile
import jsonfield
import uuidfield
from django.db import models
from django_enumfield import enum
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.conf import settings
from celery import current_task
from celery.contrib.methods import task
from distutils import dir_util

import stretch
from stretch import plugins, utils, parser
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
    name = models.TextField(unique=True)
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
        new_parser.build_and_push(self.system, self.sha)

        # Clear buffers
        shutils.rmtree(release_buffer_path)

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
    name = models.TextField(unique=True)
    release = models.ForeignKey(Release)
    auto_deploy = models.BooleanField(default=False)
    hosts = generic.GenericRelation(Host)
    groups = generic.GenericRelation(Group)
    system = models.ForeignKey(System)

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

        total_steps = 7

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
        release_config = pull_release(new_release, buffers['new'], True)

        # Parse sources
        new_source = parser.SourceParser(buffers['new'], new_release)
        existing_source = None
        if existing_release:
            existing_source = parser.SourceParser(buffers['existing'],
                                                  existing_release)

        # Run build plugins unique
        new_parser.run_build_plugins(self)

        # Run pre-deploy plugins
        update_status(2, 'Running pre-deploy plugins')
        new_source.run_pre_deploy_plugins(existing_source, self)

        # Parse release configuration
        update_status(3, 'Parsing release configuration')
        node_configs = parser.parse_release_config(release_config,
                                                   new_release,
                                                   existing_release, self)

        # Push images and configurations to nodes
        update_status(4, 'Pushing images and configurations to nodes')

        hosts = {}
        for instance in NodeInstance.objects.get(environment=self):
            host, node_name = instance.host, instance.node.name
            if hosts.has_key(host):
                if node_name not in hosts[host]:
                    hosts[host].append(node_name)
            else:
                hosts[host] = [node_name]

        # Transport templates
        # TODO: lock
        local_path = os.path.join(self.system.name, self.name)
        templates_path = os.path.join(settings.CACHE_DIR, 'templates',
                                      local_path)
        utils.clear_path(templates_path)
        new_source.mount_templates(templates_path)

        # Pull release
        fqdns = map(lambda x: x.fqdn, hosts.keys())
        params = [new_release.sha, settings.REGISTRY_URL, self.system.name,
                  local_path]
        salt_client.cmd_batch(fqdns, 'stretch.pull', params,
                              batch=str(settings.BATCH_SIZE),
                              expr_form='list')

        # Clear template mount after all nodes have pulled
        shutil.rmtree(templates_path)

        # Change release
        update_status(5, 'Changing release')

        # Switch buffers
        update_status(6, 'Switching buffers')

        # Clear existing buffer
        utils.clear_path(buffers['existing'])
        dir_util.copy_tree(buffers['new'], buffers['existing'])
        utils.clear_path(buffers['new'])

        # Run post-deploy plugins
        update_status(7, 'Running post-deploy plugins')
        new_source.run_post_deploy_plugins(existing_source, self)

    @task
    def deploy_source(self, source):
        backend = stretch.backend

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
    name = models.TextField(unique=True)
    system = models.ForeignKey(System)


class NodeInstance(ChildModel):
    id = uuidfield.UUIDField(auto=True, primary_key=True)
    node = models.ForeignKey(Node)
    environment = models.ForeignKey(Environment)

    def autoload(self, app_path):
        group = self.parent
        host = group.parent
        host.call_salt('stretch.autoload', self.pk, app_path)

    def restart(self):
        pass


class Group(ChildModel):
    name = models.TextField(unique=True)
    environment = models.ForeignKey(Environment)
    minimum_nodes = models.IntegerField(default=1)
    maximum_nodes = models.IntegerField(default=None)
    node = models.ForeignKey(Node)
    hosts = generic.GenericRelation(Host)
    instances = generic.GenericRelation(NodeInstance)

    def scale_up(self, amount):
        self.check_valid_amount(self.host_count + amount)

        for _ in range(amount):
            host = backend.create_host_with_node.delay(self.node)
            host.parent = self
            host.save()

        # Change group load balancer
        # trigger: reset env-wide configuration

    def scale_down(self, amount):
        self.check_valid_amount(self.host_count - amount)

        hosts = self.hosts[0:amount]

        # remove hosts from self
        for host in hosts:
            host.parent = None
        # trigger: reset env-wide configuration
        self.environment # reset configuration generating hostlists 
        # from the groups
        [host.delete.delay() for host in hosts]

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
