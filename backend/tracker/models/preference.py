from uuid import uuid7

from django.conf import settings
from django.db import models

from common.models.timestamp import TimeStampModel
from tracker.constants.categories import (
    DEFAULT_GROUP_BY,
    DEFAULT_SORT_BY,
    GroupBy,
    SortBy,
)


class KanbanPreference(TimeStampModel):
    """The only stored view setting: how a user likes a project's board."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kanban_preferences",
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="+"
    )
    group_by = models.CharField(
        max_length=16, choices=GroupBy.choices, default=DEFAULT_GROUP_BY
    )
    sort_by = models.CharField(
        max_length=16, choices=SortBy.choices, default=DEFAULT_SORT_BY
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project"], name="unique_kanban_preference"
            )
        ]
