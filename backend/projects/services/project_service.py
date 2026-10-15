from datetime import date, timedelta

from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from accounts.models import User
from accounts.services import reauth_service
from accounts.services.reauth_service import Reauth
from common.exception.domain import ConflictException
from common.validators.date import validate_date_range
from common.validators.tags import normalize_tags, validate_tag_count
from projects import permissions
from projects.constants import actions, error_codes, fields, limits, messages
from projects.constants.permissions import PROJECT_FIELD_PERMISSIONS
from projects.models import Membership, Project, ProjectTag
from projects.services import (
    access,
    activity,
    hooks,
    join_code,
    tag_service,
)

_UNSET = object()


def tag_names(project: Project) -> list[str]:
    return tag_service.names(ProjectTag, "project", project)


def _set_tags(project: Project, names: list[str]) -> dict | None:
    return tag_service.sync(ProjectTag, "project", project, names)


def list_memberships(user: User) -> QuerySet[Membership]:
    """The caller's projects. Soft-deleted ones show only to their owner."""
    return (
        access.memberships_for(user)
        .filter(Q(project__is_deleted=False) | Q(is_owner=True))
        .annotate(member_count=Count("project__memberships"))
        .order_by("-project__created_at")
    )


@transaction.atomic
def create(
    user: User,
    *,
    name: str,
    task_key: str,
    description: str = "",
    start_date: date | None = None,
    end_date: date | None = None,
    tags: list[str] | None = None,
    ip: str | None = None,
) -> Membership:
    validate_date_range(start_date, end_date)
    names = normalize_tags(tags or [])
    validate_tag_count(names, fields.MAX_TAGS_PER_PROJECT)
    project = Project(
        owner=user,
        name=name.strip(),
        description=description,
        task_key=task_key.upper(),
        start_date=start_date,
        end_date=end_date,
    )
    join_code.save_with_unique_code(project)
    membership = Membership.objects.create(user=user, project=project, is_owner=True)
    _set_tags(project, names)
    hooks.run_project_created(project)
    activity.log(
        project,
        user,
        actions.PROJECT_CREATED,
        actions.ENTITY_PROJECT,
        project.pk,
        {"name": project.name},
        ip,
    )
    return membership


@transaction.atomic
def update(membership: Membership, data: dict, ip: str | None = None) -> Membership:
    project = membership.project
    access.ensure_writable(project)
    access.ensure_not_demo(project)
    data = dict(data)
    is_listed = data.pop("is_listed", _UNSET)
    permissions.require_fields(
        membership, [(name, PROJECT_FIELD_PERMISSIONS[name]) for name in data]
    )
    if is_listed is not _UNSET:
        permissions.require_owner(membership)

    if "task_key" in data:
        data["task_key"] = data["task_key"].upper()
    if "name" in data:
        data["name"] = data["name"].strip()
    validate_date_range(
        data.get("start_date", project.start_date),
        data.get("end_date", project.end_date),
    )

    changes: dict[str, dict] = {}
    names = None
    if "tags" in data:
        names = normalize_tags(data.pop("tags"))
        validate_tag_count(names, fields.MAX_TAGS_PER_PROJECT)
    for name, value in data.items():
        old = getattr(project, name)
        if old != value:
            changes[name] = {"from": _plain(old), "to": _plain(value)}
            setattr(project, name, value)
    if is_listed is not _UNSET and project.is_listed != is_listed:
        changes["is_listed"] = {"from": project.is_listed, "to": is_listed}
        project.is_listed = is_listed
        project.listed_at = timezone.now() if is_listed else None
    if names is not None and (tag_change := _set_tags(project, names)):
        changes["tags"] = tag_change

    if changes:
        project.save()
        activity.log(
            project,
            membership.user,
            actions.PROJECT_UPDATED,
            actions.ENTITY_PROJECT,
            project.pk,
            changes,
            ip,
        )
    return membership


def _plain(value: object) -> object:
    return value.isoformat() if isinstance(value, date) else value


@transaction.atomic
def archive(membership: Membership, ip: str | None = None) -> Membership:
    permissions.require_owner(membership)
    project = membership.project
    access.ensure_not_demo(project)
    access.ensure_writable(project)
    project.archived_at = timezone.now()
    project.save(update_fields=["archived_at", "updated_at"])
    activity.log(
        project,
        membership.user,
        actions.PROJECT_ARCHIVED,
        actions.ENTITY_PROJECT,
        project.pk,
        ip=ip,
    )
    return membership


@transaction.atomic
def unarchive(membership: Membership, ip: str | None = None) -> Membership:
    permissions.require_owner(membership)
    project = membership.project
    access.ensure_not_demo(project)
    if not project.is_archived:
        raise ConflictException(
            messages.PROJECT_NOT_ARCHIVED, error_code=error_codes.PROJECT_NOT_ARCHIVED
        )
    project.archived_at = None
    project.save(update_fields=["archived_at", "updated_at"])
    activity.log(
        project,
        membership.user,
        actions.PROJECT_UNARCHIVED,
        actions.ENTITY_PROJECT,
        project.pk,
        ip=ip,
    )
    return membership


@transaction.atomic
def soft_delete(
    membership: Membership, reauth: Reauth, ip: str | None = None, verifier=None
) -> Membership:
    permissions.require_owner(membership)
    access.ensure_not_demo(membership.project)
    reauth_service.confirm(membership.user, reauth, verifier)
    project = membership.project
    project.delete()
    activity.log(
        project,
        membership.user,
        actions.PROJECT_DELETED,
        actions.ENTITY_PROJECT,
        project.pk,
        ip=ip,
    )
    return membership


def deletion_scheduled_for(project: Project):
    if not project.is_deleted or project.deleted_at is None:
        return None
    return project.deleted_at + timedelta(days=limits.PROJECT_DELETION_GRACE_DAYS)


@transaction.atomic
def restore(membership: Membership, ip: str | None = None) -> Membership:
    permissions.require_owner(membership)
    project = membership.project
    access.ensure_not_demo(project)
    if not project.is_deleted:
        raise ConflictException(
            messages.PROJECT_NOT_DELETED, error_code=error_codes.PROJECT_NOT_DELETED
        )
    if deletion_scheduled_for(project) <= timezone.now():
        raise ConflictException(
            messages.RESTORE_WINDOW_OVER, error_code=error_codes.RESTORE_WINDOW_OVER
        )
    project.is_deleted = False
    project.deleted_at = None
    project.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    activity.log(
        project,
        membership.user,
        actions.PROJECT_RESTORED,
        actions.ENTITY_PROJECT,
        project.pk,
        ip=ip,
    )
    return membership


@transaction.atomic
def regenerate_join_code(
    membership: Membership, reauth: Reauth, ip: str | None = None, verifier=None
) -> Membership:
    permissions.require_owner(membership)
    project = membership.project
    access.ensure_not_demo(project)
    reauth_service.confirm(membership.user, reauth, verifier)
    access.ensure_writable(project)
    join_code.save_with_unique_code(project)
    activity.log(
        project,
        membership.user,
        actions.JOIN_CODE_REGENERATED,
        actions.ENTITY_PROJECT,
        project.pk,
        ip=ip,
    )
    return membership


def purge_deleted_projects() -> int:
    """Hard delete projects whose 7-day undo window is over."""
    cutoff = timezone.now() - timedelta(days=limits.PROJECT_DELETION_GRACE_DAYS)
    expired = list(
        Project.all_objects.filter(
            is_deleted=True, deleted_at__lt=cutoff, demo_key__isnull=True
        )
    )
    for project in expired:
        hooks.run_project_purging(project)
        _set_tags(project, [])
    # all_objects is a plain manager, so this really deletes the rows.
    Project.all_objects.filter(pk__in=[p.pk for p in expired]).delete()
    return len(expired)
