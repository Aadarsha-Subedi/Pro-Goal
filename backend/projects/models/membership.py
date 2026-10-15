from uuid import uuid7

from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models.timestamp import TimeStampModel


class Membership(TimeStampModel):
    """One row per user and project. Exactly one member per project is owner."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="memberships"
    )
    joined_at = models.DateTimeField(default=timezone.now)
    is_owner = models.BooleanField(default=False)

    class Meta:
        ordering = ["joined_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"], name="unique_membership"
            ),
            models.UniqueConstraint(
                fields=["project"],
                condition=models.Q(is_owner=True),
                name="one_owner_per_project",
            ),
        ]
