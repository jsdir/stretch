import os.path
import shutils
import json
import tarfile
import jsonfield
from django.db import models
from django_enumfield import enum
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from celery import current_task
from celery.contrib.methods import task
from distutils import dir_util

from stretch import plugins, utils, parser
from stretch.utils import salt_client


class AuditedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

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

    def __init__(self, system):
        self.name = utils.generate_memorable_name()
        self.sha = utils.generate_random_hex(40)
        self.system = system

    @classmethod
    def create_from_sources(cls, system, sources):
        """
        Release.create_from_sources(system, {git_source: {'ref': new_ref}})

        sources = {
            <Source>: {'ref': 'someref'},
        }
        """
        # Create release
        release = cls(system)

        # Create buffers
        buffers = {}
        release_buffer_path = os.path.join(settings.TEMP_DIR, release.sha)
        for name in ('release', 'source'):
            buffer_path = os.path.join(release_buffer_path, name)
            if os.path.isdir(buffer_path):
                shutils.rmtree(buffer_path)
            utils.makedirs(buffer_path)
            buffers[name] = buffer_path

        # Pull from sources
        source_config = {}

        # Acquire lock
        lock = utils.lock('source')
        with lock:
            for source, pull_options in sources:
                source.pull(pull_options)
                source_path = source.get_path()

                # Copy source into source buffer
                dir_util.copy_tree(source_path, buffers['source'])

                # Create BuildParser
                source = parser.SourceParser(buffers['source'], release, True)

                # Decrypt
                source.decrypt_secrets()

                # Compile and merge release configuration
                utils.update(source_config, source.get_release_config())

                # Merge to release buffer
                source.copy_to_buffer(buffers['release'])

        # Archive the release
        release_dir = os.path.join(settings.DATA_DIR, 'releases', release.sha)
        utils.makedirs(release_dir)

        # Write release configuration
        with open(os.path.join(release_dir, '%s.json' % release.sha)) as f:
            f.write(json.dumps(source_config))

        # Tar release buffer
        tar_path = os.path.join(release_dir, '%s.tar.gz' % release.sha)
        tar_file = tarfile.open(tar_path, 'w:gz')
        tar_file.add(buffers['release'], '/')
        tar_file.close()

        # Build docker images
        release_source = parser.SourceParser(buffers['release'], release)
        release_source.build_and_push(release.system, release.sha)

        # Run build plugins
        release_source.run_build_plugins()

        # Clear buffers
        shutils.rmtree(release_buffer_path)

        release.save()

        # Push release to all auto-deploying environments
        for environment in Environment.objects.filter(auto_deploy=True):
            environment.deploy(release)

        return release


class Host(models.Model):
    fqdn = models.TextField(unique=True)
    hostname = models.TextField()
    managed = models.BooleanField()

    parent_content_type = models.ForeignKey(ContentType)
    parent_object_id = models.PositiveIntegerField()
    parent = generic.GenericForeignKey('parent_content_type',
                                       'parent_object_id')

    def add_node(self, node):
        node_instance = NodeInstance(node=node, host=self)
        self.call_salt('stretch.add_node', node.node_type)
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
    system = models.ForeignKey(System)
    
    def deploy(self, release):
        result = self.deploy_task.delay(release)
        deploy = Deploy(release=release, target=self, task_id=result.id)
        deploy.save()

    @task
    def deploy_task(self, release):

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
                                       systems,
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
        if os.path.exists(buffers['new']):
            shutil.rmtree(buffers['new'])
        utils.makedirs(buffers['new'])

        # Pull new release
        release_config = pull_release(new_release, buffers['new'], True)

        # Parse sources
        new_source = parser.SourceParser(buffers['new'], new_release)
        existing_source = None
        if existing_release:
            existing_source = parser.SourceParser(buffers['existing'],
                                                  existing_release)

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

        # Change release
        update_status(5, 'Changing release')

        # Switch buffers
        update_status(6, 'Switching buffers')

        # Clear existing buffer
        shutil.rmtree(buffers['existing'])
        utils.makedirs(buffers['existing'])
        dir_util.copy_tree(buffers['new'], buffers['existing'])
        shutil.rmtree(buffers['new'])
        utils.makedirs(buffers['new'])

        # Run post-deploy plugins
        update_status(7, 'Running post-deploy plugins')
        new_source.run_post_deploy_plugins(existing_source, self)

        """
        if old_release:
            for plugin_application in old_release.plugin_applications:
                # Plugin applications need precedence
                plugin = plugins.get_objects.get(plugin_application.plugin_name)
                plugin.before_release_change(old_release, new_release, self)

        # Set new release
        current_task.update_state(state='PROGRESS',
            meta={'current': 2, 'total': 2})

        for plugin_application in new_release.plugin_applications:
            # Plugin applications need some sort of precedence
            plugin = plugins.get_objects.get(plugin_application.plugin_name)
            plugin.after_release_change(old_release, new_release, self)
        """

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
    node_type = models.TextField(unique=True)
    system = models.ForeignKey(System)


class NodeInstance(models.Model):
    node = models.ForeignKey(Node)
    host = models.ForeignKey(Host)


class Group(models.Model):
    name = models.TextField(unique=True)
    environment = models.ForeignKey(Environment)
    minimum_nodes = models.IntegerField(default=1)
    maximum_nodes = models.IntegerField(default=None)
    node = models.ForeignKey(Node)
    hosts = generic.GenericRelation(Host)

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
