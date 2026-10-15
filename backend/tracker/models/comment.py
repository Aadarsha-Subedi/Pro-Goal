from uuid import uuid7

from django.conf import settings
from django.db import models

from common.models.delete import SoftDeleteModel
from common.models.timestamp import TimeStampModel
from tracker.constants import fields


class Comment(TimeStampModel, SoftDeleteModel):
    """Flat comment on a task. A deleted comment keeps its row (who deleted it)
    but its body is hidden in responses."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    task = models.ForeignKey(
        "tracker.Task", on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    body = models.TextField(max_length=fields.COMMENT_BODY_MAX_LENGTH)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    class Meta:
        ordering = ["created_at"]
