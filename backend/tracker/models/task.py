from uuid import uuid7

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from common.models.delete import SoftDeleteModel
from common.models.timestamp import TimeStampModel
from tracker.constants import fields


class Task(TimeStampModel, SoftDeleteModel):
    """A unit of work. Shown as `<project task_key>-<number>`; addressed by
    number in URLs so renaming the key never breaks a link."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="tasks"
    )
    number = models.PositiveIntegerField()
    title = models.CharField(max_length=fields.TASK_TITLE_MAX_LENGTH)
    description = models.TextField(blank=True)
    status = models.ForeignKey(
        "tracker.Status", on_delete=models.RESTRICT, related_name="tasks"
    )
    priority = models.ForeignKey(
        "tracker.Priority", on_delete=models.RESTRICT, related_name="tasks"
    )
    start_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="subtasks"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL, through="tracker.TaskAssignee", related_name="tasks"
    )
    tags = models.ManyToManyField("projects.Tag", through="tracker.TaskTag")

    class Meta:
        ordering = ["-number"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "number"], name="unique_task_number_per_project"
            ),
            models.CheckConstraint(
                condition=Q(start_date__isnull=True)
                | Q(due_date__isnull=True)
                | Q(due_date__gte=F("start_date")),
                name="task_due_date_after_start_date",
            ),
        ]
        indexes = [models.Index(fields=["project", "is_deleted", "-number"])]

    @property
    def key(self) -> str:
        return f"{self.project.task_key}-{self.number}"

    def __str__(self) -> str:
        return f"{self.key} {self.title}"


class TaskAssignee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name="task_assignees"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="task_assignments",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["task", "user"], name="unique_task_assignee"
            )
        ]


class TaskTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="task_tags")
    tag = models.ForeignKey(
        "projects.Tag", on_delete=models.CASCADE, related_name="task_tags"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "tag"], name="unique_task_tag")
        ]
