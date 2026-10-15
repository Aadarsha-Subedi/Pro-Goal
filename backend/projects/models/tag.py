from uuid import uuid7

from django.db import models

from common.models.timestamp import TimeStampModel
from projects.constants import fields


class Tag(TimeStampModel):
    """Free-form label, stored lowercase and trimmed."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    name = models.CharField(max_length=fields.TAG_MAX_LENGTH, unique=True)
    usage_count = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.name


class ProjectTag(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="project_tags"
    )
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name="project_tags")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["project", "tag"], name="unique_project_tag"
            )
        ]
