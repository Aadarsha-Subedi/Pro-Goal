import logging

from django.db import transaction
from django.utils import timezone

from integrations.constants import limits
from integrations.models import OutboxEvent
from integrations.services import outbox

logger = logging.getLogger(__name__)


def dispatch_batch() -> int:
    """Hand a batch of undispatched events to every subscriber. Rows are claimed
    with SKIP LOCKED so two workers never take the same event. A subscriber that
    fails is retried on the next run, up to a limit, so one bad event cannot
    block the queue forever."""
    handled = 0
    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("project")
            .filter(dispatched_at__isnull=True)
            .order_by("created_at", "id")[: limits.DISPATCH_BATCH_SIZE]
        )
        for event in events:
            try:
                with transaction.atomic():
                    for subscriber in list(outbox.subscribers):
                        subscriber(event)
            except Exception as exc:
                logger.exception(
                    "Outbox dispatch failed", extra={"event_id": str(event.pk)}
                )
                event.dispatch_attempts += 1
                event.dispatch_error = repr(exc)[: limits.MAX_ERROR_LENGTH]
                if event.dispatch_attempts >= limits.MAX_DISPATCH_ATTEMPTS:
                    event.dispatched_at = timezone.now()
                event.save(
                    update_fields=[
                        "dispatch_attempts",
                        "dispatch_error",
                        "dispatched_at",
                    ]
                )
                continue
            event.dispatched_at = timezone.now()
            event.save(update_fields=["dispatched_at"])
            handled += 1
    return handled
