"""Slack messages for project events. Only key, title, status, names, due date
and a link ever leave the system: never descriptions, comment text or emails."""

from integrations.constants.events import EventType
from integrations.models import OutboxEvent
from integrations.services import event_text
from integrations.services.event_text import project_url, task_url  # noqa: F401


def escape(text: str) -> str:
    """Slack treats & < > as markup."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(event: OutboxEvent, *, channel: str) -> dict:
    """The payload for one `chat.postMessage` call about `event`."""
    project = event.project
    task = event_text.task_for(event)
    headline = event_text.headline(event)

    if task is not None:
        url = event_text.task_url(project.pk, task.number)
        title_line = (
            f"*<{url}|{escape(project.task_key)}-{task.number}>* {escape(task.title)}"
        )
        assignees = ", ".join(escape(name) for name in event_text.assignee_names(task))
        fields = [
            f"*Status*\n{escape(task.status.name)}",
            f"*Assignees*\n{assignees or 'Unassigned'}",
        ]
        if task.due_date:
            fields.append(f"*Due*\n{task.due_date.isoformat()}")
        text = f"{headline}: {project.task_key}-{task.number} {task.title}"
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"{escape(headline)}\n{title_line}"},
            },
            {
                "type": "section",
                "fields": [{"type": "mrkdwn", "text": f} for f in fields],
            },
        ]
    else:
        suffix = (
            "/join-requests"
            if event.event_type == EventType.JOIN_REQUEST_CREATED
            else ""
        )
        url = event_text.project_url(project.pk, suffix)
        text = f"{headline} ({project.name})"
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{escape(headline)}\n*<{url}|{escape(project.name)}>*",
                },
            }
        ]
    return {"channel": channel, "text": text, "blocks": blocks}
