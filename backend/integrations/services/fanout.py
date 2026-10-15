"""The integrations subscriber: one delivery per interested integration."""

from django.db import transaction

from integrations.constants.statuses import IntegrationStatus
from integrations.models import DeliveryAttempt, Integration, OutboxEvent
from integrations.providers import registry


def deliver_to_integrations(event: OutboxEvent) -> None:
    from integrations.tasks import deliver

    integrations = Integration.objects.filter(
        project=event.project, status=IntegrationStatus.ACTIVE
    )
    for integration in integrations:
        provider = registry.find(integration.provider)
        # A provider never gets its own changes back.
        if provider is None or provider.code == event.source:
            continue
        for planned in provider.plan(integration, event):
            delivery, created = DeliveryAttempt.objects.get_or_create(
                outbox_event=event,
                integration=integration,
                target=planned.target,
                defaults={"event_type": event.event_type, "payload": planned.payload},
            )
            if created:
                delivery_id = str(delivery.pk)
                transaction.on_commit(
                    lambda delivery_id=delivery_id: deliver.delay(delivery_id)
                )
