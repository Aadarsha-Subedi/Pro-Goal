from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from django.http import HttpRequest


@dataclass(frozen=True)
class InboundMeta:
    """What a provider learned about an incoming call after verifying it."""

    delivery_id: str
    timestamp: datetime | None = None
    item_key: str = ""
    kind: str = "webhook"


@dataclass(frozen=True)
class DeliveryResult:
    """How one outbound attempt went. `retry_after` (seconds) means the provider
    asked us to slow down: wait, without counting an attempt or a failure."""

    ok: bool
    status_code: int | None = None
    retry_after: int | None = None
    error: str = ""
    details: dict = field(default_factory=dict)


@dataclass(frozen=True)
class PlannedDelivery:
    """One delivery a provider wants made for an event: where it goes (`target`,
    unique per event and integration) and exactly what to send."""

    target: str
    payload: dict


class Provider(ABC):
    """Role: one third-party service (Slack, later others). The framework asks a
    provider only these questions; everything else is generic."""

    code: str
    manage_permission: str

    @abstractmethod
    def verify_inbound(self, request: HttpRequest, kind: str) -> InboundMeta:
        """Check the call really came from the provider (signature, age) and
        describe it. Raise AuthenticationDeniedException if it did not."""

    @abstractmethod
    def handle_inbound(self, webhook: InboundWebhook) -> None:  # noqa: F821
        """Process a stored call. Runs in a worker."""

    def wants(self, integration: Integration, event: OutboxEvent) -> bool:  # noqa: F821
        """Whether this integration should receive `event`. Simple providers
        override this and `build_payload`; providers that fan one event out to
        several targets override `plan` instead."""
        return True

    def build_payload(self, integration: Integration, event: OutboxEvent) -> dict:  # noqa: F821
        """What to send, stored on the delivery so a replay sends the same."""
        return {}

    def plan(
        self,
        integration: Integration,  # noqa: F821
        event: OutboxEvent,  # noqa: F821
    ) -> list[PlannedDelivery]:
        """The deliveries to make for `event`: usually one, possibly several
        (a message per mapped channel plus a DM per recipient), or none."""
        if not self.wants(integration, event):
            return []
        return [PlannedDelivery("", self.build_payload(integration, event))]

    @abstractmethod
    def deliver(
        self,
        integration: Integration,  # noqa: F821
        delivery: DeliveryAttempt,  # noqa: F821
    ) -> DeliveryResult:
        """Make one outbound attempt."""

    @abstractmethod
    def revoke(self, integration: Integration) -> None:  # noqa: F821
        """Revoke the stored token at the provider. Best effort."""
