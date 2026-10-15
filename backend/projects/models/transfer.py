from uuid import uuid7

from django.conf import settings
from django.db import models

from common.models.timestamp import TimeStampModel
from projects.constants.statuses import TransferStatus


class OwnershipTransfer(TimeStampModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="transfers"
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+"
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="incoming_transfers",
    )
    status = models.CharField(
        max_length=16, choices=TransferStatus.choices, default=TransferStatus.PENDING
    )
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project"],
                condition=models.Q(status=TransferStatus.PENDING),
                name="one_pending_transfer_per_project",
            )
        ]
