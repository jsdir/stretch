from django.db import models

from stretch.models import AuditedModel
from stretch.models.validators import alphanumeric


class Environment(AuditedModel):
    """
    Stateful container for hosts, instances, and groups.
    """

    class Meta:
        app_label = 'stretch'

    name = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='environments')

    def deploy(self):
        pass
