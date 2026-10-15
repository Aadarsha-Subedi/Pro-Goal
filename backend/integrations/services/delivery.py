import logging
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from integrations.constants import limits
from integrations.constants.statuses import DeliveryStatus, IntegrationStatus
from integrations.models import DeliveryAttempt
from integrations.providers import registry
from integrations.providers.base import DeliveryResult
from integrations.services import health

logger = logging.getLogger(__name__)


def _enqueue(delivery_id: str, eta: datetime | None = None) -> None:
    from integrations.tasks import deliver

    deliver.apply_async((delivery_id,), eta=eta)


def run(delivery_id: str) -> DeliveryAttempt | None:
    """Make one attempt for a pending delivery and record the outcome. The
    row stays locked for the call, so a delivery is never sent twice at once."""
    with transaction.atomic():
        delivery = (
            DeliveryAttempt.objects.select_for_update(of=("self",))
            .select_related("integration", "integration__project")
            .filter(pk=delivery_id, status=DeliveryStatus.PENDING)
            .first()
        )
        if delivery is None:
            return None
        integration = delivery.integration
        # Sending stops while an integration needs attention or is gone; the
        # delivery stays pending and is queued again on reconnect.
        if integration.status != IntegrationStatus.ACTIVE:
            return delivery
        now = timezone.now()
        if integration.paused_until and integration.paused_until > now:
            _reschedule(delivery, integration.paused_until)
            return delivery
        provider = registry.find(integration.provider)
        if provider is None:
            _fail(delivery, "Unknown provider")
            return delivery
        try:
            result = provider.deliver(integration, delivery)
        except Exception as exc:
            logger.exception(
                "Delivery crashed", extra={"delivery_id": str(delivery.pk)}
            )
            result = DeliveryResult(ok=False, error=f"{type(exc).__name__}: {exc}")
        _apply(delivery, result)
        return delivery


def _reschedule(delivery: DeliveryAttempt, eta: datetime) -> None:
    delivery.next_retry_at = eta
    delivery.save(update_fields=["next_retry_at", "response_code", "updated_at"])
    transaction.on_commit(lambda: _enqueue(str(delivery.pk), eta))


def _fail(delivery: DeliveryAttempt, error: str) -> None:
    delivery.status = DeliveryStatus.FAILED
    delivery.error = error[: limits.MAX_ERROR_LENGTH]
    delivery.next_retry_at = None
    delivery.save(update_fields=["status", "error", "next_retry_at", "updated_at"])


def _apply(delivery: DeliveryAttempt, result: DeliveryResult) -> None:
    integration = delivery.integration
    if result.retry_after is not None:
        # The provider asked us to slow down: pause the whole integration and
        # try again later, without using an attempt or counting a failure.
        wait = min(max(result.retry_after, 1), limits.MAX_PAUSE_SECONDS)
        integration.paused_until = timezone.now() + timedelta(seconds=wait)
        integration.save(update_fields=["paused_until", "updated_at"])
        delivery.response_code = result.status_code
        _reschedule(delivery, integration.paused_until)
        return

    delivery.attempt += 1
    delivery.response_code = result.status_code
    if result.ok:
        delivery.status = DeliveryStatus.SUCCESS
        delivery.error = ""
        delivery.next_retry_at = None
        delivery.save(
            update_fields=[
                "attempt",
                "response_code",
                "status",
                "error",
                "next_retry_at",
                "updated_at",
            ]
        )
        health.record_success(integration)
        return

    delivery.error = result.error[: limits.MAX_ERROR_LENGTH]
    health.record_failure(integration)
    if delivery.attempt >= limits.MAX_ATTEMPTS:
        delivery.status = DeliveryStatus.FAILED
        delivery.next_retry_at = None
    else:
        eta = timezone.now() + limits.RETRY_DELAYS[delivery.attempt - 1]
        delivery.next_retry_at = eta
        transaction.on_commit(lambda: _enqueue(str(delivery.pk), eta))
    delivery.save(
        update_fields=[
            "attempt",
            "response_code",
            "status",
            "error",
            "next_retry_at",
            "updated_at",
        ]
    )


def replay(delivery: DeliveryAttempt) -> DeliveryAttempt:
    """Send a failed delivery again from the start."""
    delivery.status = DeliveryStatus.PENDING
    delivery.attempt = 0
    delivery.error = ""
    delivery.next_retry_at = None
    delivery.save(
        update_fields=["status", "attempt", "error", "next_retry_at", "updated_at"]
    )
    transaction.on_commit(lambda: _enqueue(str(delivery.pk)))
    return delivery


def requeue_pending(integration_id) -> int:
    """After a reconnect, send everything that waited."""
    pending = list(
        DeliveryAttempt.objects.filter(
            integration_id=integration_id, status=DeliveryStatus.PENDING
        ).values_list("pk", flat=True)
    )
    for delivery_id in pending:
        transaction.on_commit(
            lambda delivery_id=delivery_id: _enqueue(str(delivery_id))
        )
    return len(pending)
