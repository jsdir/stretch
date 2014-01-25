from django.db import models

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
