import json
from datetime import UTC, datetime
from urllib.parse import parse_qs

from django.http import HttpRequest
from slack_sdk.errors import SlackApiError

from common.exception.domain import ValidationException
from integrations.models import (
    DeliveryAttempt,
    InboundWebhook,
    Integration,
    OutboxEvent,
)
from integrations.providers.base import (
    DeliveryResult,
    InboundMeta,
    PlannedDelivery,
    Provider,
)
from integrations.services import integration_service
from integrations.slack import (
    client,
    commands,
    constants,
    events,
    messages,
    recipients,
    signature,
)


class SlackProvider(Provider):
    """Role: Slack, plugged into the integration framework."""

    code = constants.PROVIDER
    manage_permission = constants.MANAGE_PERMISSION

    def verify_inbound(self, request: HttpRequest, kind: str) -> InboundMeta:
        signature.verify(request)
        if kind == "commands":
            form = parse_qs(request.body.decode("utf-8", errors="replace"))
            trigger = (form.get("trigger_id") or [""])[0]
            if not trigger:
                raise ValidationException("Missing trigger_id.")
            return InboundMeta(delivery_id=f"cmd:{trigger}", kind="commands")
        try:
            body = json.loads(request.body)
        except ValueError:
            raise ValidationException("Invalid JSON.") from None
        stamp = body.get("event_time")
        return InboundMeta(
            delivery_id=f"evt:{body.get('event_id', '')}",
            timestamp=datetime.fromtimestamp(stamp, tz=UTC) if stamp else None,
            item_key=f"team:{body.get('team_id', '')}",
            kind="events",
        )

    def handle_inbound(self, webhook: InboundWebhook) -> None:
        if webhook.kind == "commands":
            commands.handle(webhook)
        elif webhook.kind == "events":
            events.handle(webhook)

    def plan(
        self, integration: Integration, event: OutboxEvent
    ) -> list[PlannedDelivery]:
        planned = []
        for mapping in integration.slack_mappings.all():
            if event.event_type in mapping.enabled_events:
                planned.append(
                    PlannedDelivery(
                        f"channel:{mapping.channel_id}",
                        messages.build(event, channel=mapping.channel_id),
                    )
                )
        for _user, slack_id in recipients.dm_targets(integration, event):
            planned.append(
                PlannedDelivery(
                    f"dm:{slack_id}", messages.build(event, channel=slack_id)
                )
            )
        return planned

    def deliver(
        self, integration: Integration, delivery: DeliveryAttempt
    ) -> DeliveryResult:
        payload = delivery.payload
        try:
            client.web_client(integration.get_token()).chat_postMessage(
                channel=payload["channel"],
                text=payload["text"],
                blocks=payload["blocks"],
            )
        except SlackApiError as exc:
            if client.error_code(exc) in constants.DEAD_TOKEN_ERRORS:
                # The workspace removed the app or the token was revoked.
                integration_service.mark_uninstalled(integration)
            return client.to_delivery_result(exc)
        return DeliveryResult(ok=True, status_code=200)

    def revoke(self, integration: Integration) -> None:
        client.web_client(integration.get_token()).auth_revoke()
