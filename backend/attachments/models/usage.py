from django.conf import settings
from django.db import models

from common.models.timestamp import TimeStampModel


def default_user_quota() -> int:
    return settings.USER_STORAGE_QUOTA_BYTES


def default_project_quota() -> int:
    return settings.PROJECT_STORAGE_QUOTA_BYTES


class ProjectStorageUsage(TimeStampModel):
    """Bytes used by a project's attachments, including pending reservations."""

    project = models.OneToOneField(
        "projects.Project",
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="storage_usage",
    )
    bytes_used = models.PositiveBigIntegerField(default=0)
    quota_bytes = models.PositiveBigIntegerField(default=default_project_quota)


class UserStorageUsage(TimeStampModel):
    """Bytes a user has uploaded across all projects."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name="storage_usage",
    )
    bytes_used = models.PositiveBigIntegerField(default=0)
    quota_bytes = models.PositiveBigIntegerField(default=default_user_quota)
