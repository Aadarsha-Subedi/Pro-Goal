from uuid import uuid7

from django.db import models

from common.models.timestamp import TimeStampModel


class SlackChannelMapping(TimeStampModel):
    """A Slack channel that receives some of a project's events."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    integration = models.ForeignKey(
        "integrations.Integration",
        on_delete=models.CASCADE,
        related_name="slack_mappings",
    )
    channel_id = models.CharField(max_length=32)
    channel_name = models.CharField(max_length=128)
    is_public = models.BooleanField(default=False)
    enabled_events = models.JSONField(default=list)

    class Meta:
        ordering = ["channel_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["integration", "channel_id"],
                name="unique_channel_per_integration",
            )
        ]
