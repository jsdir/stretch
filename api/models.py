from django.db import models
from django_enumfield import enum
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from tasks import git
from stretch import plugins
from stretch.utils import salt_client


class AuditedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add = True)
    updated_at = models.DateTimeField(auto_now = True)

    class Meta:
        abstract = True


class Release(AuditedModel):
    tag = models.TextField(unique=True)
    ref = models.CharField('SHA', max_length=255)

    def push():
        git.delay()


class Host(models.Model):
    fqdn = models.TextField(unique=True)
    hostname = models.TextField()
    managed = models.BooleanField()

    parent_content_type = models.ForeignKey(ContentType)
    parent_object_id = models.PositiveIntegerField()
    parent = generic.GenericForeignKey('parent_content_type',
                                       'parent_object_id')

    def add_node(self, node):
        node_instance = NodeInstance()

    def call_salt(self, *args, **kwargs):
        salt_client.cmd(self.fqdn, *args, **kwargs)


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
            backend.create_host_with_node.delay(self.node)

        # trigger: reset env-wide configuration

    def scale_down(self, amount):
        self.check_valid_amount(self.host_count - amount)

        hosts = self.hosts[0:amount]

        # remove hosts from self
        # trigger: reset env-wide configuration
        self.environment # reset configuration generating hostlists 
        # from the groups
        [host.delete.delay() for host in self.hosts[0:amount]]

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


class Environment(models.Model):
    name = models.TextField(unique=True)
    release = models.ForeignKey(Release)

    hosts = generic.GenericRelation(Host)
    
    def set_release(self, release):
        old_release = self.release
        new_release = release

        for plugin_application in old_release.plugin_applications:
            # Plugin applications need precedence
            plugin = plugins.get_objects.get(plugin_application.plugin_name)
            plugin.before_release_change(old_release, new_release, self)

        # Set new release


        for plugin_application in new_release.plugin_applications:
            # Plugin applications need some sort of precedence
            plugin = plugins.get_objects.get(plugin_application.plugin_name)
            plugin.after_release_change(old_release, new_release, self)

    def add_host(self, node_definition, minion_id=None):
        if not minion_id:
            host = backend.create_host()
        else:
            pass # create unmanaged host

        host.parent = self
        host.save()

        # Apply build
        salt_client.cmd(minion_id, 'stretch.deploy', [node_definition.type, self.release.id])

        return host


class Node(models.Model):
    environment = models.ForeignKey(Environment)
    host = models.ForeignKey(Host)


class NodeInstance(models.Model):
    environment = models.ForeignKey(Environment)
    host = models.ForeignKey(Host)


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


class DeployState(enum.Enum):
    PENDING = 0
    DEPLOYING = 1
    FINISHED = 2


class Deploy(models.Model):
    release = models.ForeignKey(Release)
    target = models.ForeignKey(Environment)
    state = enum.EnumField(DeployState, default=DeployState.PENDING)
