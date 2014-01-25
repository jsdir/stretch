import logging
import uuidfield
from twisted.internet import defer, reactor
from django.db import models

from stretch.models import AuditedModel


log = logging.getLogger(__name__)


class Instance(AuditedModel):
    """
    A running instance of a node.
    """

    class Meta:
        app_label = 'stretch'

    id = uuidfield.UUIDField(auto=True, primary_key=True)
    environment = models.ForeignKey('Environment', related_name='instances')
    host = models.ForeignKey('Host', related_name='instances')
    node = models.ForeignKey('Node', related_name='instances')

    def restart(self):
        log.info('Restarting Instance[%s]' % self.pk)
        d = defer.Deferred()
        d.callback(None)
        return d
