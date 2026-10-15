"""Reading the project activity log. Rule: holders of `activity.view` (the
owner always) see everything, every other member only their own actions."""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from django.db.models import QuerySet
from django.utils import timezone

from projects import permissions
from projects.constants import limits
from projects.constants.permissions import ACTIVITY_VIEW
from projects.models import ActivityLog, Membership


def can_view_all(membership: Membership) -> bool:
    return permissions.has_permission(membership, ACTIVITY_VIEW)


def feed(
    membership: Membership,
    *,
    actor: UUID | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> QuerySet[ActivityLog]:
    queryset = ActivityLog.objects.filter(project=membership.project).select_related(
        "actor"
    )
    if can_view_all(membership):
        if actor:
            queryset = queryset.filter(actor_id=actor)
    else:
        # Everyone else sees only what they did themselves.
        queryset = queryset.filter(actor=membership.user)
    if action:
        queryset = queryset.filter(action=action)
    if entity_type:
        queryset = queryset.filter(entity_type=entity_type)
    if created_after:
        queryset = queryset.filter(created_at__gte=created_after)
    if created_before:
        queryset = queryset.filter(created_at__lte=created_before)
    return queryset.order_by("-created_at", "-id")


def shorten(value: Any, limit: int = limits.ACTIVITY_VALUE_MAX_LENGTH) -> Any:
    """Cut long strings inside `changes` (a task description can be pages)."""
    if isinstance(value, str):
        return value if len(value) <= limit else value[:limit] + "…"
    if isinstance(value, dict):
        return {key: shorten(item, limit) for key, item in value.items()}
    if isinstance(value, list):
        return [shorten(item, limit) for item in value]
    return value


def purge_old_entries() -> int:
    """Delete entries older than the retention period (one year)."""
    cutoff = timezone.now() - timedelta(days=limits.ACTIVITY_RETENTION_DAYS)
    deleted, _ = ActivityLog.objects.filter(created_at__lt=cutoff).delete()
    return deleted
