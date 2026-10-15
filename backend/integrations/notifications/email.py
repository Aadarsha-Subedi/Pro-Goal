"""Email notifications for personal events: an outbox subscriber that mails
members who opted in (`NotificationPreference.email`, off by default)."""

from django.core.cache import cache

from accounts.models import User
from accounts.services.email_service import queue_email
from integrations.models import NotificationPreference, OutboxEvent
from integrations.services import audience, event_text

IDEMPOTENCY_KEY = "notify-email:{event_id}:{user_id}"
IDEMPOTENCY_SECONDS = 7 * 24 * 60 * 60


def compose(event: OutboxEvent) -> tuple[str, str]:
    """(subject, body) for one event: key, title, status, names, due date, link."""
    project = event.project
    headline = event_text.headline(event)
    task = event_text.task_for(event)
    if task is None:
        url = event_text.project_url(
            project.pk,
            "/join-requests" if event.event_type == "join_request_created" else "",
        )
        return (
            f"{headline} ({project.name})",
            f"{headline}\n\nProject: {project.name}\n{url}\n",
        )
    key = f"{project.task_key}-{task.number}"
    lines = [
        headline,
        "",
        f"{key}  {task.title}",
        f"Status: {task.status.name}",
        f"Assignees: {', '.join(event_text.assignee_names(task)) or 'Unassigned'}",
    ]
    if task.due_date:
        lines.append(f"Due: {task.due_date.isoformat()}")
    lines += ["", event_text.task_url(project.pk, task.number)]
    return f"{headline}: {key} {task.title}", "\n".join(lines) + "\n"


def recipients(event: OutboxEvent) -> list[User]:
    if event.event_type not in audience.PERSONAL_EVENTS:
        return []
    wanted = audience.candidate_users(event)
    if not wanted:
        return []
    members = audience.current_members(event, wanted)
    opted_in = NotificationPreference.objects.filter(
        user_id__in=members, event_type=event.event_type, email=True
    ).values_list("user_id", flat=True)
    return list(User.objects.filter(pk__in=list(opted_in), is_active=True))


def notify_by_email(event: OutboxEvent) -> None:
    """Outbox subscriber. At-least-once dispatch means this can run twice for
    one event, so each (event, person) is sent only once."""
    people = recipients(event)
    if not people:
        return
    subject, body = compose(event)
    for user in people:
        key = IDEMPOTENCY_KEY.format(event_id=event.pk, user_id=user.pk)
        if cache.add(key, 1, IDEMPOTENCY_SECONDS):
            queue_email(subject, body, user.email)
