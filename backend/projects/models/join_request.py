from uuid import uuid7

from django.conf import settings
from django.db import models

from common.models.timestamp import TimeStampModel
from projects.constants.statuses import JoinRequestStatus


class JoinRequest(TimeStampModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="join_requests"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="join_requests"
    )
    status = models.CharField(
        max_length=16,
        choices=JoinRequestStatus.choices,
        default=JoinRequestStatus.PENDING,
    )
    expires_at = models.DateTimeField()
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["project", "status"])]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"],
                condition=models.Q(status=JoinRequestStatus.PENDING),
                name="one_pending_join_request",
            )
        ]
