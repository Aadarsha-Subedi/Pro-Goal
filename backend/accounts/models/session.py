from uuid import uuid7

from django.conf import settings
from django.db import models

from common.models.timestamp import TimeStampModel


class UserSession(TimeStampModel):
    """Metadata for one Django session, so a user can list and revoke their
    own sessions. The session data itself lives in Django's cached_db store;
    `session_key` points at it."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions"
    )
    session_key = models.CharField(max_length=40, unique=True)
    device_name = models.CharField(max_length=255, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    last_seen_at = models.DateTimeField()
    remember_me = models.BooleanField(default=False)

    class Meta:
        ordering = ["-last_seen_at"]
        indexes = [models.Index(fields=["user", "-last_seen_at"])]

    def __str__(self) -> str:
        return f"{self.user_id} ({self.device_name or 'unknown device'})"
