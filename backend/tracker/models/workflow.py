from uuid import uuid7

from django.db import models
from django.db.models.functions import Lower

from common.models.timestamp import TimeStampModel
from tracker.constants import fields
from tracker.constants.categories import StatusCategory


class TaskCounter(models.Model):
    """Hands out per-project task numbers. Always read under select_for_update."""

    project = models.OneToOneField(
        "projects.Project", primary_key=True, on_delete=models.CASCADE, related_name="+"
    )
    next_number = models.PositiveIntegerField(default=1)


class Status(TimeStampModel):
    """Per-project workflow state. `category` survives renames so automations
    can rely on it."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="statuses"
    )
    name = models.CharField(max_length=fields.STATUS_NAME_MAX_LENGTH)
    category = models.CharField(max_length=16, choices=StatusCategory.choices)
    position = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "created_at"]
        verbose_name_plural = "statuses"
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "project", name="unique_status_name_per_project"
            ),
            models.UniqueConstraint(
                fields=["project"],
                condition=models.Q(is_default=True),
                name="one_default_status_per_project",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Priority(TimeStampModel):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="priorities"
    )
    name = models.CharField(max_length=fields.PRIORITY_NAME_MAX_LENGTH)
    rank = models.PositiveIntegerField(default=0)
    position = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["position", "created_at"]
        verbose_name_plural = "priorities"
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "project", name="unique_priority_name_per_project"
            ),
            models.UniqueConstraint(
                fields=["project"],
                condition=models.Q(is_default=True),
                name="one_default_priority_per_project",
            ),
        ]

    def __str__(self) -> str:
        return self.name
