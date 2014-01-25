from django.db import models

from stretch.models import AuditedModel
from stretch.models.validators import alphanumeric


class Node(AuditedModel):
    """
    Node database abstraction that allows users to bind ports and their names.
    """

    class Meta:
        app_label = 'stretch'
        unique_together = ('system', 'name')

    name = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='nodes')
