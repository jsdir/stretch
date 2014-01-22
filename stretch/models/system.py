from stretch.models import AuditedModel, Release
from stretch.models.validators import alphanumeric
from stretch.source import get_source


class System(AuditedModel):
    """
    Stateful container for environments.
    """
    name = models.TextField(unique=True, validators=[alphanumeric])

    class Meta:
        app_name = 'stretch'
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
        system_sources = sources.get_sources(self)
        if not system_sources:
            raise exceptions.UndefinedSource()
        return system_sources[0]
