from uuid import uuid7

from django.conf import settings
from django.db import models
from django.db.models import Q

from attachments.constants import limits
from attachments.constants.types import Category, Status, TargetType
from common.models.timestamp import TimeStampModel


class Attachment(TimeStampModel):
    """A file stored in R2 and attached to exactly one task, note or comment.
    Rows are hard-deleted; a `post_delete` signal frees the quota and removes
    the R2 object, so cascade deletes of the parent clean up too."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="attachments"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attachments",
    )
    task = models.ForeignKey(
        "tracker.Task",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    note = models.ForeignKey(
        "tracker.Note",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    comment = models.ForeignKey(
        "tracker.Comment",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    object_key = models.CharField(max_length=512, unique=True)
    filename = models.CharField(max_length=limits.FILENAME_MAX_LENGTH)
    content_type = models.CharField(max_length=127)
    category = models.CharField(max_length=16, choices=Category.choices)
    size_bytes = models.PositiveBigIntegerField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["project", "status"])]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(task__isnull=False, note__isnull=True, comment__isnull=True)
                    | Q(task__isnull=True, note__isnull=False, comment__isnull=True)
                    | Q(task__isnull=True, note__isnull=True, comment__isnull=False)
                ),
                name="attachment_exactly_one_target",
            )
        ]

    @property
    def target_type(self) -> str:
        if self.task_id:
            return TargetType.TASK
        return TargetType.NOTE if self.note_id else TargetType.COMMENT

    def __str__(self) -> str:
        return self.filename
