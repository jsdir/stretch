class UndefinedSource(Exception):
    """Raised if a system tries to use a source that does not exist."""
    def __str__(self):
        return 'No source defined. Add sources for the system in settings.py'
