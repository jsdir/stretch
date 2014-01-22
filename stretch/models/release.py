from django.db import models

from stretch import utils
from stretch.models import AuditedModel
from stretch.models.validators import alphanumeric


class Release(AuditedModel):
    """
    A system state that can be deployed to environments, archived, and rolled
    back to.
    """

    name = models.TextField(validators=[alphanumeric])
    tag = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='releases')

    class Meta:
        app_label = 'stretch'

    @classmethod
    def create(cls, path, tag, system):
        """
        Creates, and processes, and archives a release. Emits a
        `release_created` signal upon completion.

        :Parameters:
          - `path`: the path to create the release from.
          - `tag`: a metadata tag for the release.
          - `system`: the system to associate the release with.
        """
        release = cls(
            name=utils.generate_memorable_name(),
            tag=tag,
            system=system
        )

        # Build finished
        release.save()
        # signals.release_created.send(sender=release)
        return release
