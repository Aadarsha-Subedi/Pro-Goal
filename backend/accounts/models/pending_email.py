from uuid import uuid7

from django.conf import settings
from django.db import models

from common.models.timestamp import TimeStampModel


class PendingEmailChange(TimeStampModel):
    """A requested new login address, waiting for the owner of that address to
    confirm it. One per user; asking again replaces it. Nothing about the
    account changes until the link sent to `new_email` is used."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pending_email_change",
    )
    new_email = models.EmailField()

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.new_email}"
