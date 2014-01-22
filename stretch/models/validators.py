from django.core.validators import RegexValidator


alphanumeric = RegexValidator(r'^[a-zA-Z0-9_\-]*$', 'Only alphanumeric '
    'characters, underscores, and hyphens are allowed.')
