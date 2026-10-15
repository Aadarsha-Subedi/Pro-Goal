"""Turns project activity into catalog events. Registered as an activity
listener, so it runs in the transaction of the change that caused the event."""

from integrations.constants.events import EventType
from integrations.services import outbox
from projects.models import ActivityLog


def _base(row: ActivityLog) -> dict:
    return {
        "project_name": row.project.name,
        "actor_id": str(row.actor_id) if row.actor_id else None,
    }


def _task_snapshot(row: ActivityLog) -> dict:
    from tracker.models import Task

    task = (
        Task.all_objects.filter(pk=row.entity_id).only("number", "title").first()
        if row.entity_id
        else None
    )
    if task is None:
        return {}
    return {
        "task_id": str(row.entity_id),
        "task_number": task.number,
        "title": task.title,
    }


def _assignee_ids(row: ActivityLog) -> list[str]:
    from tracker.models import TaskAssignee

    return sorted(
        str(pk)
        for pk in TaskAssignee.objects.filter(task_id=row.entity_id).values_list(
            "user_id", flat=True
        )
    )


def events_for(row: ActivityLog) -> list[tuple[EventType, dict]]:
    """The catalog events an activity row stands for (possibly none)."""
    base = _base(row)
    action = row.action
    changes = row.changes or {}

    if action == "task.created":
        snapshot = {
            **base,
            "task_id": str(row.entity_id),
            "task_number": changes.get("number"),
            "title": changes.get("title"),
        }
        found = [(EventType.TASK_CREATED, snapshot)]
        # People assigned while the task is created are assigned too.
        for user_id in _assignee_ids(row):
            found.append(
                (EventType.TASK_ASSIGNED, {**snapshot, "assignee_id": user_id})
            )
        return found
    if action == "task.updated":
        snapshot = {**base, **_task_snapshot(row)}
        found = [(EventType.TASK_UPDATED, {**snapshot, "changes": changes})]
        if "assignees" in changes:
            before = set(changes["assignees"].get("from", []))
            after = set(changes["assignees"].get("to", []))
            for user_id in sorted(after - before):
                found.append(
                    (EventType.TASK_ASSIGNED, {**snapshot, "assignee_id": user_id})
                )
        return found
    if action == "comment.created":
        return [
            (
                EventType.COMMENT_ADDED,
                {
                    **base,
                    "comment_id": str(row.entity_id),
                    "task_number": changes.get("task"),
                },
            )
        ]
    if action == "join_request.approved":
        return [(EventType.MEMBER_JOINED, {**base, "user_id": changes.get("user")})]
    if action in ("member.removed", "member.left"):
        return [
            (
                EventType.MEMBER_REMOVED,
                {
                    **base,
                    "user_id": str(row.entity_id),
                    "left": action == "member.left",
                },
            )
        ]
    if action == "project.archived":
        return [(EventType.PROJECT_ARCHIVED, base)]
    if action == "join_request.created":
        return [
            (
                EventType.JOIN_REQUEST_CREATED,
                {
                    **base,
                    "request_id": str(row.entity_id),
                    "requester_id": base["actor_id"],
                },
            )
        ]
    return []


def on_activity(row: ActivityLog) -> None:
    for event_type, payload in events_for(row):
        outbox.emit(row.project, event_type, payload)
