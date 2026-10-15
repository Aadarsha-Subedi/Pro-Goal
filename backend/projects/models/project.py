from uuid import uuid7

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from common.models.delete import SoftDeleteModel
from common.models.timestamp import TimeStampModel
from projects.constants import fields


class Project(TimeStampModel, SoftDeleteModel):
    """The tenant. Everything project-scoped is reached through a Membership.
    `objects` hides soft-deleted projects, `all_objects` sees them."""

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)

    name = models.CharField(max_length=fields.PROJECT_NAME_MAX_LENGTH)
    description = models.TextField(blank=True)
    task_key = models.CharField(max_length=fields.TASK_KEY_MAX_LENGTH)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    join_code = models.CharField(max_length=fields.JOIN_CODE_LENGTH, unique=True)
    is_listed = models.BooleanField(default=False)
    # When the owner last made the project visible on the explore page.
    listed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    # Stable id of a shared demo project (see `seed_demo_projects`). Demo
    # projects belong to the system user and are read-only for everyone else.
    demo_key = models.CharField(max_length=40, null=True, blank=True, unique=True)
    # The demo project this one was copied from, if any.
    copied_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="copies",
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_projects",
    )
    tags = models.ManyToManyField("projects.Tag", through="projects.ProjectTag")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(start_date__isnull=True)
                | Q(end_date__isnull=True)
                | Q(end_date__gte=F("start_date")),
                name="project_end_date_after_start_date",
            )
        ]

    @property
    def is_demo(self) -> bool:
        return self.demo_key is not None

    @property
    def is_archived(self) -> bool:
        return self.archived_at is not None

    def __str__(self) -> str:
        return self.name
