from django.db import models
from django_enumfield import enum

from tasks import git
from stretch import plugins


class Release(models.Model):
    tag = models.TextField(unique=True)
    ref = models.CharField('SHA', max_length=255)

    def push():
        git.delay()


class Environment(models.Model):
    name = models.TextField(unique=True)
    release = models.ForeignKey(Release)
    
    def set_release(self, release):
        old_release = self.release #?
        new_release = release

        for plugin_application in old_release.plugin_applications:
            # Plugin applications need precedence
            plugin = plugins.get_objects.get(plugin_application.plugin_name)

        # Set new release

        for plugin_application in new_release.plugin_applications:
            # Plugin applications need some sort of precedence
            plugin = plugins.get_objects.get(plugin_application.plugin_name)


class Group(models.Model):
    name = models.TextField(unique=True)
    environment = models.ForeignKey(Environment)
    minimum_nodes = models.IntegerField(default=1)
    maximum_nodes = models.IntegerField(default=-1)


class Node(models.Model):
    environment = models.ForeignKey(Environment)
    group = models.ForeignKey(Group)


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
