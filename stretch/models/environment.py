from django.db import models

from stretch.models import AuditedModel
from stretch.models.validators import alphanumeric


class Environment(AuditedModel):
    """
    Stateful container for hosts, instances, and groups.
    """

    name = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='environments')

    class Meta:
        app_label = 'stretch'
