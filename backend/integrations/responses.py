from dataclasses import dataclass

from common.response.domain import BaseResponseData
from integrations.models import DeliveryAttempt, Integration
from projects.responses import public_user


def _iso(value) -> str | None:
    return value.isoformat() if value else None


@dataclass(frozen=True)
class IntegrationData(BaseResponseData):
    """Health and identity of an integration. Tokens are never included."""

    integration: Integration

    def to_dict(self) -> dict:
        item = self.integration
        return {
            "id": str(item.pk),
            "provider": item.provider,
            "status": item.status,
            "external_workspace_id": item.external_workspace_id,
            "installed_by": public_user(item.installed_by)
            if item.installed_by
            else None,
            "consecutive_failures": item.consecutive_failures,
            "paused_until": _iso(item.paused_until),
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }


@dataclass(frozen=True)
class DeliveryData(BaseResponseData):
    delivery: DeliveryAttempt

    def to_dict(self) -> dict:
        item = self.delivery
        return {
            "id": str(item.pk),
            "direction": item.direction,
            "event_type": item.event_type,
            "status": item.status,
            "attempt": item.attempt,
            "response_code": item.response_code,
            "next_retry_at": _iso(item.next_retry_at),
            "error": item.error,
            "created_at": item.created_at.isoformat(),
            "updated_at": item.updated_at.isoformat(),
        }
