from uuid import uuid7

from django.conf import settings
from django.db import models

from common.models.timestamp import TimeStampModel
from tracker.constants import fields


class Note(TimeStampModel):
    """Project knowledge, separate from tasks. Raw markdown is the only source
    of truth; `version` supports optimistic locking."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="notes"
    )
    title = models.CharField(max_length=fields.NOTE_TITLE_MAX_LENGTH)
    body = models.TextField(blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    version = models.PositiveIntegerField(default=1)
    tags = models.ManyToManyField("projects.Tag", through="tracker.NoteTag")
    tasks = models.ManyToManyField(
        "tracker.Task", through="tracker.TaskNote", related_name="notes"
    )

    class Meta:
        ordering = ["-updated_at"]
        indexes = [models.Index(fields=["project", "-updated_at"])]

    def __str__(self) -> str:
        return self.title


class NoteRevision(models.Model):
    """One row per save, so history can be listed and compared."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="revisions")
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=fields.NOTE_TITLE_MAX_LENGTH)
    body = models.TextField(blank=True)
    edited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["note", "version"], name="unique_note_revision_version"
            )
        ]


class NoteTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="note_tags")
    tag = models.ForeignKey(
        "projects.Tag", on_delete=models.CASCADE, related_name="note_tags"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["note", "tag"], name="unique_note_tag")
        ]


class TaskNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    task = models.ForeignKey(
        "tracker.Task", on_delete=models.CASCADE, related_name="task_notes"
    )
    note = models.ForeignKey(Note, on_delete=models.CASCADE, related_name="task_notes")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["task", "note"], name="unique_task_note")
        ]
