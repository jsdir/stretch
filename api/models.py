from django.db import models


class Environment(models.Model):
    name = models.TextField(unique=True)
    promotes_to = models.ForeignKey('self')
    entrypoint = models.BooleanField()


class Group(models.Model):
    name = models.TextField(unique=True)
    environment = models.ForeignKey(Environment)
    minimum_nodes = models.IntegerField()
    maximum_nodes = models.IntegerField()


class Node(models.Model):
    environment = models.ForeignKey(Environment)
    group = models.ForeignKey(Group)


class Trigger(models.Model):
    environment = models.ForeignKey(Environment)


class Action(models.Model):
    trigger = models.OneToOneField(Trigger)


class Event(models.Model):
    trigger = models.OneToOneField(Trigger)


class Metric(models.Model):
    environment = models.ForeignKey(Environment)


class Promotion(models.Model):
    environment = models.ForeignKey(Environment)
