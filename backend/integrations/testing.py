"""A provider for tests: signature `X-Fake-Signature: ok`, scriptable results.
Never registered outside tests."""

from datetime import datetime

from django.http import HttpRequest

from common.exception.domain import AuthenticationDeniedException
from integrations.constants import error_codes, messages
from integrations.providers.base import DeliveryResult, InboundMeta, Provider


class FakeProvider(Provider):
    code = "fake"
    manage_permission = "integration.slack.manage"  # reuse a registered code

    def __init__(self) -> None:
        self.delivered: list[dict] = []
        self.handled: list[str] = []
        self.revoked: list[str] = []
        self.results: list[DeliveryResult] = []  # consumed in order, then ok
        self.wanted: set[str] | None = None  # None = every event
        self.revoke_error: Exception | None = None
        self.handle_error: Exception | None = None

    def verify_inbound(self, request: HttpRequest, kind: str) -> InboundMeta:
        if request.headers.get("X-Fake-Signature") != "ok":
            raise AuthenticationDeniedException(
                messages.INVALID_SIGNATURE, error_code=error_codes.INVALID_SIGNATURE
            )
        stamp = request.headers.get("X-Fake-Timestamp")
        return InboundMeta(
            delivery_id=request.headers.get("X-Fake-Delivery", "d-1"),
            timestamp=datetime.fromisoformat(stamp) if stamp else None,
            item_key=request.headers.get("X-Fake-Item", ""),
        )

    def handle_inbound(self, webhook) -> None:
        if self.handle_error:
            raise self.handle_error
        self.handled.append(webhook.delivery_id)

    def wants(self, integration, event) -> bool:
        return self.wanted is None or event.event_type in self.wanted

    def build_payload(self, integration, event) -> dict:
        return {"event": event.event_type, **event.payload}

    def deliver(self, integration, delivery) -> DeliveryResult:
        self.delivered.append(delivery.payload)
        if self.results:
            return self.results.pop(0)
        return DeliveryResult(ok=True, status_code=200)

    def revoke(self, integration) -> None:
        if self.revoke_error:
            raise self.revoke_error
        self.revoked.append(integration.get_token())
