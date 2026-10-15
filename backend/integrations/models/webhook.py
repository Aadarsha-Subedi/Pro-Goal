from uuid import uuid7

from django.db import models

from integrations.constants.statuses import WebhookStatus


class InboundWebhook(models.Model):
    """A call from a provider, stored before it is processed. The unique
    delivery id makes a replayed call harmless."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    provider = models.CharField(max_length=32)
    kind = models.CharField(max_length=32, default="webhook")
    delivery_id = models.CharField(max_length=128)
    raw_payload = models.TextField()
    content_type = models.CharField(max_length=100, blank=True)
    # What the call is about (for example a task) and when the provider says
    # it happened, to drop events that arrive out of order.
    item_key = models.CharField(max_length=200, blank=True)
    provider_timestamp = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=WebhookStatus.choices, default=WebhookStatus.RECEIVED
    )
    error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "delivery_id"], name="unique_webhook_delivery"
            )
        ]
        indexes = [models.Index(fields=["provider", "item_key", "-provider_timestamp"])]
