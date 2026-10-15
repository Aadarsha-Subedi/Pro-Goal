from datetime import date, timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from accounts.models import User
from common.exception.domain import ConflictException, ValidationException
from common.validators.date import validate_date_range
from common.validators.tags import normalize_tags, validate_tag_count
from projects import permissions
from projects.constants import permissions as codes
from projects.models import Membership
from projects.services import access as project_access
from projects.services import activity, tag_service
from tracker.constants import actions, error_codes, fields, limits, messages
from tracker.constants.categories import StatusCategory
from tracker.models import (
    Priority,
    Status,
    Task,
    TaskAssignee,
    TaskCounter,
    TaskTag,
)
from tracker.services import access

TASK_FIELD_PERMISSIONS = {
    "title": codes.TASK_TITLE_CHANGE,
    "description": codes.TASK_DESCRIPTION_CHANGE,
    "status": codes.TASK_STATUS_CHANGE,
    "priority": codes.TASK_PRIORITY_CHANGE,
    "assignees": codes.TASK_ASSIGNEES_CHANGE,
    "start_date": codes.TASK_START_DATE_CHANGE,
    "due_date": codes.TASK_DUE_DATE_CHANGE,
    "tags": codes.TASK_TAGS_CHANGE,
    "parent": codes.TASK_PARENT_CHANGE,
}


def _next_number(membership: Membership) -> int:
    counter, _ = TaskCounter.objects.select_for_update().get_or_create(
        project=membership.project
    )
    number = counter.next_number
    TaskCounter.objects.filter(pk=counter.pk).update(next_number=F("next_number") + 1)
    return number


def _default(model, project):
    return model.objects.filter(project=project, is_default=True).first()


def _status_in_project(membership: Membership, status_id: UUID) -> Status:
    return access.get_status(membership.project, status_id)


def _assignees(membership: Membership, user_ids: list[UUID]) -> list[User]:
    unique = list(dict.fromkeys(user_ids))
    members = {
        m.user_id: m.user
        for m in Membership.objects.filter(
            project=membership.project, user_id__in=unique
        ).select_related("user")
    }
    missing = [str(uid) for uid in unique if uid not in members]
    if missing:
        raise ValidationException(
            messages.ASSIGNEE_NOT_MEMBER,
            errors=[{"field": "assignees", "message": messages.ASSIGNEE_NOT_MEMBER}],
            error_code=error_codes.ASSIGNEE_NOT_MEMBER,
        )
    return [members[uid] for uid in unique]


def _set_assignees(task: Task, users: list[User]) -> dict | None:
    before = set(task.task_assignees.values_list("user_id", flat=True))
    after = {u.pk for u in users}
    if before == after:
        return None
    task.task_assignees.exclude(user_id__in=after).delete()
    TaskAssignee.objects.bulk_create(
        TaskAssignee(task=task, user=u) for u in users if u.pk not in before
    )
    return {"from": sorted(map(str, before)), "to": sorted(map(str, after))}


def _tags(names: list[str]) -> list[str]:
    cleaned = normalize_tags(names)
    validate_tag_count(cleaned, fields.MAX_TAGS_PER_ITEM)
    return cleaned


def _open_subtasks(task: Task) -> bool:
    return (
        Task.objects.filter(parent=task)
        .exclude(status__category=StatusCategory.DONE)
        .exists()
    )


def _check_parent(membership: Membership, task: Task | None, number: int) -> Task:
    """Validate a parent choice for `task` (None for a task being created)."""
    parent = Task.objects.filter(project=membership.project, number=number).first()
    if parent is None or (task is not None and parent.pk == task.pk):
        raise ValidationException(
            errors=[{"field": "parent", "message": messages.INVALID_PARENT}],
            error_code=error_codes.INVALID_PARENT,
        )
    if parent.parent_id is not None:
        raise ConflictException(
            messages.SUBTASK_OF_SUBTASK, error_code=error_codes.SUBTASK_OF_SUBTASK
        )
    if task is not None and Task.objects.filter(parent=task).exists():
        raise ConflictException(
            messages.TASK_HAS_SUBTASKS, error_code=error_codes.TASK_HAS_SUBTASKS
        )
    return parent


@transaction.atomic
def create(
    membership: Membership,
    data: dict,
    *,
    parent_number: int | None = None,
    ip: str | None = None,
) -> Task:
    permissions.require_permission(membership, codes.TASK_CREATE)
    project = membership.project
    project_access.ensure_writable(project)
    validate_date_range(data.get("start_date"), data.get("due_date"), "due_date")
    names = _tags(data.get("tags", []))
    assignees = _assignees(membership, data.get("assignees", []))

    status = (
        _status_in_project(membership, data["status"])
        if data.get("status")
        else _default(Status, project)
    )
    priority = (
        access.get_priority(project, data["priority"])
        if data.get("priority")
        else _default(Priority, project)
    )
    parent = (
        _check_parent(membership, None, parent_number)
        if parent_number is not None
        else None
    )

    task = Task.objects.create(
        project=project,
        number=_next_number(membership),
        title=data["title"].strip(),
        description=data.get("description", ""),
        status=status,
        priority=priority,
        start_date=data.get("start_date"),
        due_date=data.get("due_date"),
        parent=parent,
        created_by=membership.user,
    )
    _set_assignees(task, assignees)
    tag_service.sync(TaskTag, "task", task, names)
    activity.log(
        project,
        membership.user,
        actions.TASK_CREATED,
        actions.ENTITY_TASK,
        task.pk,
        {"number": task.number, "title": task.title},
        ip,
    )
    return task


@transaction.atomic
def update(
    membership: Membership, task: Task, data: dict, ip: str | None = None
) -> Task:
    project = membership.project
    project_access.ensure_writable(project)
    permissions.require_fields(
        membership, [(name, TASK_FIELD_PERMISSIONS[name]) for name in data]
    )
    data = dict(data)
    changes: dict[str, dict] = {}

    start = data.get("start_date", task.start_date)
    due = data.get("due_date", task.due_date)
    validate_date_range(start, due, "due_date")

    if "status" in data:
        status = _status_in_project(membership, data["status"])
        if (
            status.category == StatusCategory.DONE
            and status.pk != task.status_id
            and _open_subtasks(task)
        ):
            raise ConflictException(
                messages.OPEN_SUBTASKS, error_code=error_codes.OPEN_SUBTASKS
            )
        if status.pk != task.status_id:
            changes["status"] = {"from": task.status.name, "to": status.name}
            task.status = status
    if "priority" in data:
        priority = access.get_priority(project, data["priority"])
        if priority.pk != task.priority_id:
            changes["priority"] = {"from": task.priority.name, "to": priority.name}
            task.priority = priority
    if "parent" in data:
        number = data["parent"]
        if number is None:
            new_parent = None
        else:
            new_parent = _check_parent(membership, task, number)
        if (new_parent.pk if new_parent else None) != task.parent_id:
            changes["parent"] = {
                "from": task.parent.number if task.parent_id else None,
                "to": number,
            }
            task.parent = new_parent
    for name in ("title", "description", "start_date", "due_date"):
        if name in data:
            value = data[name].strip() if name == "title" else data[name]
            old = getattr(task, name)
            if old != value:
                changes[name] = {"from": _plain(old), "to": _plain(value)}
                setattr(task, name, value)

    if changes:
        task.save()
    if "assignees" in data and (
        diff := _set_assignees(task, _assignees(membership, data["assignees"]))
    ):
        changes["assignees"] = diff
    if "tags" in data and (
        diff := tag_service.sync(TaskTag, "task", task, _tags(data["tags"]))
    ):
        changes["tags"] = diff
    if changes:
        task.save(update_fields=["updated_at"])
        activity.log(
            project,
            membership.user,
            actions.TASK_UPDATED,
            actions.ENTITY_TASK,
            task.pk,
            changes,
            ip,
        )
    return task


def _plain(value: object) -> object:
    return value.isoformat() if isinstance(value, date) else value


def deletion_scheduled_for(task: Task):
    if not task.is_deleted or task.deleted_at is None:
        return None
    return task.deleted_at + timedelta(days=limits.TASK_DELETION_GRACE_DAYS)


@transaction.atomic
def delete(membership: Membership, task: Task, ip: str | None = None) -> Task:
    permissions.require_permission(membership, codes.TASK_DELETE)
    project_access.ensure_writable(membership.project)
    now = timezone.now()
    family = [task.pk, *Task.objects.filter(parent=task).values_list("pk", flat=True)]
    Task.all_objects.filter(pk__in=family).update(
        is_deleted=True, deleted_at=now, updated_at=now
    )
    task.is_deleted, task.deleted_at = True, now
    activity.log(
        membership.project,
        membership.user,
        actions.TASK_DELETED,
        actions.ENTITY_TASK,
        task.pk,
        {"number": task.number, "subtasks": len(family) - 1},
    )
    return task


@transaction.atomic
def restore(membership: Membership, task: Task, ip: str | None = None) -> Task:
    permissions.require_permission(membership, codes.TASK_DELETE)
    project_access.ensure_writable(membership.project)
    if not task.is_deleted:
        raise ConflictException(
            messages.TASK_NOT_DELETED, error_code=error_codes.TASK_NOT_DELETED
        )
    if deletion_scheduled_for(task) <= timezone.now():
        raise ConflictException(
            messages.TASK_RESTORE_WINDOW_OVER,
            error_code=error_codes.TASK_RESTORE_WINDOW_OVER,
        )
    if task.parent_id and task.parent.is_deleted:
        raise ConflictException(
            messages.INVALID_PARENT, error_code=error_codes.INVALID_PARENT
        )
    deleted_at = task.deleted_at
    now = timezone.now()
    # The parent comes back with the subtasks that were deleted along with it.
    Task.all_objects.filter(
        Q(pk=task.pk) | Q(parent=task), is_deleted=True, deleted_at=deleted_at
    ).update(is_deleted=False, deleted_at=None, updated_at=now)
    task.is_deleted, task.deleted_at = False, None
    activity.log(
        membership.project,
        membership.user,
        actions.TASK_RESTORED,
        actions.ENTITY_TASK,
        task.pk,
        {"number": task.number},
        ip,
    )
    return task


def purge_deleted_tasks() -> int:
    """Hard delete tasks whose 7-day undo window is over."""
    cutoff = timezone.now() - timedelta(days=limits.TASK_DELETION_GRACE_DAYS)
    expired = Task.all_objects.filter(is_deleted=True, deleted_at__lt=cutoff)
    ids = list(expired.values_list("pk", flat=True))
    tag_service.release(
        list(TaskTag.objects.filter(task_id__in=ids).values_list("tag_id", flat=True))
    )
    # all_objects is a plain manager, so this really deletes the rows.
    Task.all_objects.filter(pk__in=ids).delete()
    return len(ids)
