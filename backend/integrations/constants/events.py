"""The event catalog: what the outbox can carry."""

from django.db import models


class EventType(models.TextChoices):
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_ASSIGNED = "task_assigned"
    TASK_DUE_SOON = "task_due_soon"
    TASK_OVERDUE = "task_overdue"
    COMMENT_ADDED = "comment_added"
    MEMBER_JOINED = "member_joined"
    MEMBER_REMOVED = "member_removed"
    PROJECT_ARCHIVED = "project_archived"
    JOIN_REQUEST_CREATED = "join_request_created"


class Source(models.TextChoices):
    """Where a change came from, so a provider never echoes its own changes."""

    WEB = "web"
    SYSTEM = "system"  # scheduled jobs
    SLACK = "slack"
