from uuid import uuid7

from django.conf import settings
from django.db import models

from projects.constants import fields


class ActivityLog(models.Model):
    """Append-only record of project changes. Rows are never updated."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="activity"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    action = models.CharField(max_length=fields.ACTIVITY_ACTION_MAX_LENGTH)
    entity_type = models.CharField(max_length=fields.ENTITY_TYPE_MAX_LENGTH)
    entity_id = models.UUIDField(null=True, blank=True)
    changes = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["project", "-created_at"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Activity log rows are append-only.")
        super().save(*args, **kwargs)
