from uuid import uuid7

from django.conf import settings
from django.db import models

from security.constants.events import EventType


class SecurityEvent(models.Model):
    """Append-only account security record, readable by its own user. Separate
    from the project activity log. Never stores passwords, tokens or the
    attempted email address."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="security_events",
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_name = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError("Security events are append-only.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.event_type} ({self.user_id})"
