import logging
from django.db import models
from twisted.internet import defer

from stretch.models import AuditedModel


log = logging.getLogger(__name__)


class Host(AuditedModel):
    """
    Hosts can either be managed or unmanaged. Managed hosts are created when a
    group is scaled, but unmanaged hosts have no parent group since they are
    created and provisioned manually.
    """

    class Meta:
        app_label = 'stretch'
        unique_together = ('environment', 'name')

    #fqdn = models.TextField(unique=True)
    name = models.TextField(unique=True)
    #hostname = models.TextField()
    #domain_name = models.TextField(null=True)
    group = models.ForeignKey('Group', related_name='hosts', null=True)
    environment = models.ForeignKey('Environment', related_name='hosts')
    #address = models.GenericIPAddressField()

    def restart_instances(self, groups):
        log.info('Restarting instances for Host[%s]...' % self.pk)
        restart_tasks = []

        if self.group:
            if self.group not in groups:
                batch_size = self.group.batch_size
                groups[self.group] = defer.DeferredSemaphore(batch_size)
            semaphore = groups[self.group]

            # Run restarts with batch size semaphore to maintain the
            # availability of the group
            for instance in self.instances.all():
                restart_tasks.append(semaphore.run(instance.restart()))
        else:
            # Run all restarts at once since there is no group
            for instance in self.instances.all():
                restart_tasks.append(instance.restart())

        return defer.DeferredList(restart_tasks)

    @property
    def agent(self):
        return None
