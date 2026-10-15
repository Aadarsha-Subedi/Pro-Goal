"""Lifecycle states for join requests and ownership transfers."""

from django.db import models


class JoinRequestStatus(models.TextChoices):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class TransferStatus(models.TextChoices):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
