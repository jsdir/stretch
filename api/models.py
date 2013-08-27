from django.db import models
from django_enumfield import enum


class Environment(models.Model):
    name = models.TextField(unique=True)


class Group(models.Model):
    name = models.TextField(unique=True)
    environment = models.ForeignKey(Environment)
    minimum_nodes = models.IntegerField(default=1)
    maximum_nodes = models.IntegerField(default=-1)


class Node(models.Model):
    environment = models.ForeignKey(Environment)
    group = models.ForeignKey(Group)


class Trigger(models.Model):
    environment = models.ForeignKey(Environment)


class Action(models.Model):
    trigger = models.OneToOneField(Trigger)

    class Meta:
        abstract = True


class ScaleActionDirection(enum.Enum):
    UP = 0
    DOWN = 1


class ScaleAction(Action):
    direction = enum.EnumField(ScaleActionDirection)


class Event(models.Model):
    trigger = models.OneToOneField(Trigger)


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


class Release(models.Model):
    ref = models.CharField('SHA', max_length=255)
