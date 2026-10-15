from uuid import uuid7

from django.conf import settings
from django.db import models

from common.models.timestamp import TimeStampModel


class NotificationPreference(TimeStampModel):
    """How one person wants to hear about one kind of event. `slack_dm` is
    used by the Slack integration; `email` is stored for the email
    notifications that come later and has no effect yet."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    event_type = models.CharField(max_length=32)
    email = models.BooleanField(default=False)
    slack_dm = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event_type"], name="unique_preference_per_event"
            )
        ]
