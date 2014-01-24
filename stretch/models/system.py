from django.db import models

from stretch import utils, source
from stretch.models import AuditedModel, Release
from stretch.models.validators import alphanumeric


class System(AuditedModel):
    """
    Stateful container for environments.
    """

    class Meta:
        app_label = 'stretch'

    name = models.TextField(unique=True, validators=[alphanumeric])

    def create_release(self, options):
        path, tag = self.source.clone(options)
        return Release.create(path, tag, system=self)

    @property
    @utils.memoized
    def source(self):
        """
        Returns the correct source to be used with the system. (Only one
        source is used per system for now. Multiple source handling may be
        implemented.)
        """
        sources = source.get_sources(self)
        if not sources:
            raise source.NoSourceException()
        return sources[0]
