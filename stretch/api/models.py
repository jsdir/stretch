from django.db import models
from django_enumfield import enum
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from celery import current_task
from celery.contrib.methods import task

from stretch import plugins
from stretch import utils
from stretch.utils import salt_client


class AuditedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        abstract = True


class Release(AuditedModel):
    tag = models.TextField(unique=True)
    ref = models.CharField('SHA', max_length=255)

    @classmethod
    def create_from_sources(cls, sources):
        """
        Release.create_from_sources({git_source: {'ref': new_ref}})

        sources = {
            <Source>: {'ref': 'someref'},
        }
        """

        # Acquire lock
        lock = utils.lock('source_pull')
        with lock:
            for source, pull_options in sources:
                source.pull(pull_options)
                path = source.get_path()


            # Process the release
            pass


        release = cls()
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
    
    def deploy(self, release):
        result = self.deploy_task.delay(release)
        deploy = Deploy(release=release, target=self, task_id=result.id)
        deploy.save()

    @task()
    def deploy_task(self, release):
        old_release = self.release
        new_release = release

        current_task.update_state(state='PROGRESS',
            meta={'current': 1, 'total': 2})

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
