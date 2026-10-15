from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from projects import permissions
from projects.constants import permissions as codes
from projects.models import Membership
from projects.services import access as project_access
from projects.services import activity
from tracker.constants import actions, error_codes, messages
from tracker.models import Status, Task
from tracker.services import access, ordering


def list_statuses(membership: Membership) -> QuerySet[Status]:
    return Status.objects.filter(project=membership.project)


@transaction.atomic
def create(
    membership: Membership,
    *,
    name: str,
    category: str,
    position: int | None = None,
    is_default: bool = False,
    ip: str | None = None,
) -> Status:
    permissions.require_permission(membership, codes.STATUS_CREATE)
    project = membership.project
    project_access.ensure_writable(project)
    name = name.strip()
    ordering.ensure_unique_name(Status, project, name)
    status = Status.objects.create(
        project=project,
        name=name,
        category=category,
        position=ordering.next_position(Status, project),
    )
    if position is not None:
        ordering.move(Status, project, status, position)
    if is_default:
        ordering.make_default(Status, project, status)
    activity.log(
        project,
        membership.user,
        actions.STATUS_CREATED,
        actions.ENTITY_STATUS,
        status.pk,
        {"name": name, "category": category},
        ip,
    )
    return status


def _remaining_in_category(status: Status) -> int:
    others = Status.objects.filter(project=status.project, category=status.category)
    return others.exclude(pk=status.pk).count()


@transaction.atomic
def update(
    membership: Membership, status_id: UUID, data: dict, ip: str | None = None
) -> Status:
    permissions.require_permission(membership, codes.STATUS_UPDATE)
    project = membership.project
    project_access.ensure_writable(project)
    status = access.get_status(project, status_id)
    changes: dict = {}

    if "name" in data and data["name"].strip() != status.name:
        name = data["name"].strip()
        ordering.ensure_unique_name(Status, project, name, status.pk)
        changes["name"] = {"from": status.name, "to": name}
        status.name = name
    if "category" in data and data["category"] != status.category:
        if _remaining_in_category(status) == 0:
            raise access.conflict(
                messages.LAST_IN_CATEGORY, error_codes.LAST_IN_CATEGORY
            )
        changes["category"] = {"from": status.category, "to": data["category"]}
        status.category = data["category"]
    if changes:
        status.save()
    if "position" in data and data["position"] != status.position:
        changes["position"] = {"from": status.position, "to": data["position"]}
        ordering.move(Status, project, status, data["position"])
    if data.get("is_default") and not status.is_default:
        ordering.make_default(Status, project, status)
        changes["is_default"] = {"from": False, "to": True}

    if changes:
        activity.log(
            project,
            membership.user,
            actions.STATUS_UPDATED,
            actions.ENTITY_STATUS,
            status.pk,
            changes,
            ip,
        )
    return status


@transaction.atomic
def delete(
    membership: Membership,
    status_id: UUID,
    move_to: UUID | None = None,
    ip: str | None = None,
) -> None:
    permissions.require_permission(membership, codes.STATUS_DELETE)
    project = membership.project
    project_access.ensure_writable(project)
    status = access.get_status(project, status_id)
    ordering.ensure_deletable(status)
    if _remaining_in_category(status) == 0:
        raise access.conflict(messages.LAST_IN_CATEGORY, error_codes.LAST_IN_CATEGORY)
    in_use = Task.all_objects.filter(status=status).exists()
    replacement = ordering.replacement_for(Status, status, move_to, in_use)
    if replacement is not None:
        Task.all_objects.filter(status=status).update(status=replacement)
    status.delete()
    activity.log(
        project,
        membership.user,
        actions.STATUS_DELETED,
        actions.ENTITY_STATUS,
        status_id,
        {"name": status.name, "moved_to": str(replacement.pk) if replacement else None},
        ip,
    )
