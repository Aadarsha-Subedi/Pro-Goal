from celery import shared_task

from integrations.constants.tasks import QUEUE


@shared_task(queue=QUEUE)
def dispatch_outbox() -> int:
    from integrations.services import dispatcher

    return dispatcher.dispatch_batch()


@shared_task(queue=QUEUE)
def deliver(delivery_id: str) -> None:
    from integrations.services import delivery

    delivery.run(delivery_id)


@shared_task(queue=QUEUE)
def process_webhook(webhook_id: str) -> None:
    from integrations.services import webhook_service

    webhook_service.process(webhook_id)


@shared_task(queue=QUEUE)
def scan_due_dates() -> int:
    from integrations.services import scan

    return scan.scan_due_dates()


@shared_task(queue=QUEUE)
def purge_old_records() -> dict:
    """Delivery attempts, processed webhooks and dispatched events are kept 30 days."""
    from datetime import timedelta

    from django.utils import timezone

    from integrations.constants import limits
    from integrations.constants.statuses import DeliveryStatus, WebhookStatus
    from integrations.models import DeliveryAttempt, InboundWebhook, OutboxEvent

    cutoff = timezone.now() - timedelta(days=limits.RETENTION_DAYS)
    deliveries, _ = (
        DeliveryAttempt.objects.filter(created_at__lt=cutoff)
        .exclude(status=DeliveryStatus.PENDING)
        .delete()
    )
    webhooks, _ = (
        InboundWebhook.objects.filter(received_at__lt=cutoff)
        .exclude(status=WebhookStatus.RECEIVED)
        .delete()
    )
    events, _ = OutboxEvent.objects.filter(
        dispatched_at__isnull=False, dispatched_at__lt=cutoff
    ).delete()
    return {"deliveries": deliveries, "webhooks": webhooks, "events": events}
