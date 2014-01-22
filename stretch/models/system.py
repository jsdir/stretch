from django.db import models

from stretch import utils
from stretch.models import AuditedModel, Release
from stretch.models.validators import alphanumeric
from stretch.source import get_sources


class System(AuditedModel):
    """
    Stateful container for environments.
    """
    name = models.TextField(unique=True, validators=[alphanumeric])

    class Meta:
        db_table = 'stretch_system'

    def create_release(self, options):
        return Release.create(self.source.pull(options), system=self)

    @property
    @utils.memoized
    def source(self):
        """
        Returns the correct source to be used with the system. (Only one
        source is used per system for now. Multiple source handling may be
        implemented.)
        """
        sources = get_sources(self)
        if not sources:
            raise exceptions.UndefinedSource()
        return sources[0]
