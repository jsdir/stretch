from django.db import models
from celery import group
from celery.contrib.methods import task

from stretch.models import AuditedModel
from stretch.models.validators import alphanumeric


class Group(AuditedModel):
    """
    A group is a collection of homogeneous hosts. Each host in a group runs one
    instance that runs the the node associated with the group.
    """

    class Meta:
        app_label = 'stretch'
        unique_together = ('environment', 'name')

    name = models.TextField(validators=[alphanumeric])
    environment = models.ForeignKey('Environment', related_name='groups')
    minimum_nodes = models.IntegerField(default=0)
    maximum_nodes = models.IntegerField(null=True)
    node = models.ForeignKey('Node', related_name='groups')
    #load_balancer = models.OneToOneField(
    #    'LoadBalancer', null=True, related_name='group'
    #)

    def scale_up(self, amount):
        self._check_valid_amount(self.hosts.count() + amount)
        group(self._create_host.s() for _ in xrange(amount))().get()

    def scale_down(self, amount):
        self._check_valid_amount(self.hosts.count() - amount)
        hosts = self.hosts.all()[0:amount]
        group(self._delete_host.s(host.pk) for host in hosts)().get()

    def scale_to(self, amount):
        relative_amount = amount - self.hosts.count()
        if relative_amount > 0:
            self.scale_up(relative_amount)
        elif relative_amount < 0:
            self.scale_down(-relative_amount)

    def _check_valid_amount(self, amount):
        if self.maximum_nodes == None:
            valid = amount >= self.minimum_nodes
        else:
            valid = self.minimum_nodes <= amount <= self.maximum_nodes
        if not valid:
            raise ScaleException('invalid scaling amount')

    @task
    def _create_host(self):
        Host.create(self.environment, self)

    @task
    def _delete_host(self, host_id):
        Host.objects.get(pk=host_id).delete()


class ScaleException(Exception): pass

