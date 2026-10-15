from uuid import uuid7

from django.db import models

from common.models.timestamp import TimeStampModel
from integrations.constants.statuses import DeliveryStatus, Direction


class DeliveryAttempt(TimeStampModel):
    """One delivery to (or from) a provider and how it went. The row is updated
    on every attempt (`attempt` counts them), which is what replay needs."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    integration = models.ForeignKey(
        "integrations.Integration", on_delete=models.CASCADE, related_name="deliveries"
    )
    direction = models.CharField(
        max_length=3, choices=Direction.choices, default=Direction.OUT
    )
    event_type = models.CharField(max_length=32)
    outbox_event = models.ForeignKey(
        "integrations.OutboxEvent",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="deliveries",
    )
    status = models.CharField(
        max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    attempt = models.PositiveSmallIntegerField(default=0)
    response_code = models.PositiveSmallIntegerField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    # Where it goes when one event makes several deliveries (a Slack channel,
    # a person). Empty for providers that send one message per event.
    target = models.CharField(max_length=128, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["integration", "-created_at"])]
        constraints = [
            models.UniqueConstraint(
                fields=["outbox_event", "integration", "target"],
                name="one_delivery_per_event_integration_target",
            )
        ]
