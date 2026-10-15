from collections.abc import Callable

from django.db import transaction

from integrations.constants.events import EventType
from integrations.context import current_source
from integrations.models import OutboxEvent
from projects.models import Project

# Who receives each outbox event. Integrations are the first subscriber; email
# notifications (feature 8) will be another. Subscribers must be idempotent:
# dispatch is at least once.
Subscriber = Callable[[OutboxEvent], None]
subscribers: list[Subscriber] = []


def emit(
    project: Project,
    event_type: EventType,
    payload: dict,
    *,
    source: str | None = None,
    dedupe_key: str | None = None,
) -> OutboxEvent | None:
    """Save an event in the caller's transaction and schedule its dispatch for
    after commit. Returns None if `dedupe_key` was already used."""
    if dedupe_key is not None:
        event, created = OutboxEvent.objects.get_or_create(
            dedupe_key=dedupe_key,
            defaults={
                "project": project,
                "event_type": event_type,
                "payload": payload,
                "source": source or current_source(),
            },
        )
        if not created:
            return None
    else:
        event = OutboxEvent.objects.create(
            project=project,
            event_type=event_type,
            payload=payload,
            source=source or current_source(),
        )
    transaction.on_commit(_kick)
    return event


def _kick() -> None:
    from integrations.tasks import dispatch_outbox

    dispatch_outbox.delay()
