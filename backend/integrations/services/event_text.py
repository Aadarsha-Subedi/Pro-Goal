"""Plain-text description of an outbox event, shared by every channel that
announces events (Slack, email). Only key, title, status, names, due date and a
link: never descriptions, comment text or email addresses. Channels escape the
text for their own format."""

from django.conf import settings

from accounts.models import User
from integrations.constants.events import EventType
from integrations.models import OutboxEvent
from projects.models import Project
from tracker.models import Task


def task_url(project_id, number: int) -> str:
    return f"{settings.FRONTEND_URL}/projects/{project_id}/tasks/{number}"


def project_url(project_id, suffix: str = "") -> str:
    return f"{settings.FRONTEND_URL}/projects/{project_id}{suffix}"


def first_name(user_id: str | None) -> str:
    user = (
        User.objects.filter(pk=user_id).only("first_name").first() if user_id else None
    )
    return user.first_name if user else "Someone"


def task_for(event: OutboxEvent) -> Task | None:
    """The task an event is about, if it is about one."""
    if not event.event_type.startswith(("task_", "comment_")):
        return None
    payload, project = event.payload, event.project
    queryset = Task.all_objects.select_related("status", "priority").filter(
        project=project
    )
    if payload.get("task_id"):
        return queryset.filter(pk=payload["task_id"]).first()
    if payload.get("task_number"):
        return queryset.filter(number=payload["task_number"]).first()
    return None


def change_summary(changes: dict) -> str:
    parts = []
    for name, change in changes.items():
        label = name.replace("_", " ")
        if name in (
            "status",
            "priority",
            "due_date",
            "start_date",
            "title",
        ) and isinstance(change, dict):
            old = change.get("from") or "none"
            new = change.get("to") or "none"
            parts.append(f"{label}: {old} → {new}")
        else:
            # Descriptions, tags and assignee ids are named but never quoted.
            parts.append(label)
    return ", ".join(parts)


def headline(event: OutboxEvent) -> str:
    payload = event.payload
    kind = event.event_type
    actor = first_name(payload.get("actor_id"))
    if kind == EventType.TASK_CREATED:
        return f"{actor} created a task"
    if kind == EventType.TASK_UPDATED:
        return f"{actor} updated a task: {change_summary(payload.get('changes', {}))}"
    if kind == EventType.TASK_ASSIGNED:
        return f"Task assigned to {first_name(payload.get('assignee_id'))}"
    if kind == EventType.TASK_DUE_SOON:
        return "Task due soon"
    if kind == EventType.TASK_OVERDUE:
        return "Task overdue"
    if kind == EventType.COMMENT_ADDED:
        return f"{actor} commented on a task"
    if kind == EventType.MEMBER_JOINED:
        return f"{first_name(payload.get('user_id'))} joined the project"
    if kind == EventType.MEMBER_REMOVED:
        verb = "left" if payload.get("left") else "was removed from"
        return f"{first_name(payload.get('user_id'))} {verb} the project"
    if kind == EventType.PROJECT_ARCHIVED:
        return "The project was archived"
    if kind == EventType.JOIN_REQUEST_CREATED:
        return f"{first_name(payload.get('requester_id'))} asked to join the project"
    return kind.replace("_", " ").capitalize()


def assignee_names(task: Task) -> list[str]:
    return sorted(user.first_name for user in task.assignees.all())


def project_of(event: OutboxEvent) -> Project:
    return event.project
