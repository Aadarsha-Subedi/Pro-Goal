from django.db import models


class IntegrationStatus(models.TextChoices):
    ACTIVE = "active"
    NEEDS_ATTENTION = "needs_attention"
    DISCONNECTED = "disconnected"


class DeliveryStatus(models.TextChoices):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class Direction(models.TextChoices):
    IN = "in"
    OUT = "out"


class WebhookStatus(models.TextChoices):
    RECEIVED = "received"
    PROCESSED = "processed"
    IGNORED = "ignored"
    FAILED = "failed"
