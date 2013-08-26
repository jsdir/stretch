from django.db import models


class Environment(models.Model):
    name = models.CharField(unique=True)


class Node(models.Model):
    environment = models.ForeignKey(Environment)


class Group(models.Model):
    environment = models.ForeignKey(Environment)


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
