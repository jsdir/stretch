from django.db import models


class AuditedModel(models.Model):
    """
    Provides `created_at` and `updated_at` fields to indicate when the model
    was modified.
    """
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        abstract = True
