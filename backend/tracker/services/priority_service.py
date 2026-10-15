from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from projects import permissions
from projects.constants import permissions as codes
from projects.models import Membership
from projects.services import access as project_access
from projects.services import activity
from tracker.constants import actions
from tracker.models import Priority, Task
from tracker.services import access, ordering


def list_priorities(membership: Membership) -> QuerySet[Priority]:
    return Priority.objects.filter(project=membership.project)


@transaction.atomic
def create(
    membership: Membership,
    *,
    name: str,
    position: int | None = None,
    is_default: bool = False,
    ip: str | None = None,
) -> Priority:
    permissions.require_permission(membership, codes.PRIORITY_CREATE)
    project = membership.project
    project_access.ensure_writable(project)
    name = name.strip()
    ordering.ensure_unique_name(Priority, project, name)
    spot = ordering.next_position(Priority, project)
    priority = Priority.objects.create(
        project=project, name=name, position=spot, rank=spot + 1
    )
    if position is not None:
        ordering.move(Priority, project, priority, position)
    if is_default:
        ordering.make_default(Priority, project, priority)
    activity.log(
        project,
        membership.user,
        actions.PRIORITY_CREATED,
        actions.ENTITY_PRIORITY,
        priority.pk,
        {"name": name},
        ip,
    )
    return priority


@transaction.atomic
def update(
    membership: Membership, priority_id: UUID, data: dict, ip: str | None = None
) -> Priority:
    permissions.require_permission(membership, codes.PRIORITY_UPDATE)
    project = membership.project
    project_access.ensure_writable(project)
    priority = access.get_priority(project, priority_id)
    changes: dict = {}

    if "name" in data and data["name"].strip() != priority.name:
        name = data["name"].strip()
        ordering.ensure_unique_name(Priority, project, name, priority.pk)
        changes["name"] = {"from": priority.name, "to": name}
        priority.name = name
        priority.save(update_fields=["name", "updated_at"])
    if "position" in data and data["position"] != priority.position:
        changes["position"] = {"from": priority.position, "to": data["position"]}
        ordering.move(Priority, project, priority, data["position"])
    if data.get("is_default") and not priority.is_default:
        ordering.make_default(Priority, project, priority)
        changes["is_default"] = {"from": False, "to": True}

    if changes:
        activity.log(
            project,
            membership.user,
            actions.PRIORITY_UPDATED,
            actions.ENTITY_PRIORITY,
            priority.pk,
            changes,
            ip,
        )
    return priority


@transaction.atomic
def delete(
    membership: Membership,
    priority_id: UUID,
    move_to: UUID | None = None,
    ip: str | None = None,
) -> None:
    permissions.require_permission(membership, codes.PRIORITY_DELETE)
    project = membership.project
    project_access.ensure_writable(project)
    priority = access.get_priority(project, priority_id)
    ordering.ensure_deletable(priority)
    in_use = Task.all_objects.filter(priority=priority).exists()
    replacement = ordering.replacement_for(Priority, priority, move_to, in_use)
    if replacement is not None:
        Task.all_objects.filter(priority=priority).update(priority=replacement)
    priority.delete()
    activity.log(
        project,
        membership.user,
        actions.PRIORITY_DELETED,
        actions.ENTITY_PRIORITY,
        priority_id,
        {
            "name": priority.name,
            "moved_to": str(replacement.pk) if replacement else None,
        },
        ip,
    )
