from django.db import models
from celery import current_task
from celery.contrib.methods import task
from celery.utils.log import get_task_logger

from stretch.models import AuditedModel, Deploy
from stretch.models.validators import alphanumeric


log = get_task_logger(__name__)


class Environment(AuditedModel):
    """
    Stateful container for hosts, instances, and groups.
    """

    class Meta:
        app_label = 'stretch'
        unique_together = ('system', 'name')

    name = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='environments')
    release = models.ForeignKey('Release', null=True)

    @task
    def deploy(self, release):
        """
        Deploys a release to the environment.

        TODO: Use a lock to prevent multiple deploys from running
        simultaneously on the same environment.

        :Parameters:
          - `release`: the release to deploy.
        """
        log.info('Deploying %s to %s/%s' % (
            release, self.system.name, self.name
        ))

        if release != self.release:
            # Keep track of deploys
            deploy = Deploy.create(self, release, current_task)
            # Start deploy
            deploy.run()
            # Set new current release
            self.release = release

        log.info('Successfully deployed %s to %s/%s' % (
            release, self.system.name, self.name
        ))

    @property
    def node_map(self):
        return dict((node.name, node.pk) for node in self.system.nodes.all())
