import os
from django.db import models
from django.conf import settings

from stretch import utils
from stretch.snapshot import Snapshot
from stretch.models import AuditedModel
from stretch.models.validators import alphanumeric


class Release(AuditedModel):
    """
    A system state that can be deployed to environments, archived, and rolled
    back to.
    """

    class Meta:
        app_label = 'stretch'
        unique_together = ('system', 'name', 'tag')

    name = models.TextField(validators=[alphanumeric])
    tag = models.TextField(validators=[alphanumeric])
    system = models.ForeignKey('System', related_name='releases')

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
            tag=tag or utlis.generate_random_hex(8),
            system=system
        )

        # Create snapshot
        snapshot = Snapshot(path)

        # Build release from snapshot
        snapshot.archive(release)

        # Build finished
        release.save()

        return release

    @property
    def archive_path(self):
        """
        Returns the archive directory for the release.
        """
        return os.path.join(settings.STRETCH_DATA_DIR, 'releases',
                            str(self.pk), 'snapshot.tar.gz')

    def get_snapshot(self):
        return Snapshot.create_from_archive(self.archive_path)
