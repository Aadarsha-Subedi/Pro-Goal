import logging

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from integrations.constants import limits
from integrations.constants.statuses import WebhookStatus
from integrations.models import InboundWebhook
from integrations.providers import registry

logger = logging.getLogger(__name__)


def receive(
    provider_code: str, request: HttpRequest, kind: str = "webhook"
) -> tuple[InboundWebhook, bool]:
    """Verify, store and queue an incoming provider call. Returns the stored
    call and whether it is new; a repeated delivery id is accepted but not
    processed again."""
    provider = registry.get(provider_code)
    meta = provider.verify_inbound(request, kind)
    webhook, created = InboundWebhook.objects.get_or_create(
        provider=provider.code,
        delivery_id=meta.delivery_id,
        defaults={
            "kind": meta.kind or kind,
            "raw_payload": request.body.decode("utf-8", errors="replace"),
            "content_type": request.content_type or "",
            "item_key": meta.item_key,
            "provider_timestamp": meta.timestamp,
        },
    )
    if created:
        webhook_id = str(webhook.pk)
        transaction.on_commit(lambda: _enqueue(webhook_id))
    return webhook, created


def _enqueue(webhook_id: str) -> None:
    from integrations.tasks import process_webhook

    process_webhook.delay(webhook_id)


def process(webhook_id: str) -> InboundWebhook | None:
    """Run the provider's handler for a stored call. Anything older than what
    was already applied for the same item is dropped."""
    webhook = InboundWebhook.objects.filter(
        pk=webhook_id, status=WebhookStatus.RECEIVED
    ).first()
    if webhook is None:
        return None
    if (
        webhook.item_key
        and webhook.provider_timestamp
        and InboundWebhook.objects.filter(
            provider=webhook.provider,
            item_key=webhook.item_key,
            status=WebhookStatus.PROCESSED,
            provider_timestamp__gt=webhook.provider_timestamp,
        ).exists()
    ):
        webhook.status = WebhookStatus.IGNORED
    else:
        try:
            registry.get(webhook.provider).handle_inbound(webhook)
            webhook.status = WebhookStatus.PROCESSED
        except Exception as exc:
            logger.exception(
                "Inbound webhook failed", extra={"webhook_id": str(webhook.pk)}
            )
            webhook.status = WebhookStatus.FAILED
            webhook.error = f"{type(exc).__name__}: {exc}"[: limits.MAX_ERROR_LENGTH]
    webhook.processed_at = timezone.now()
    webhook.save(update_fields=["status", "error", "processed_at"])
    return webhook
