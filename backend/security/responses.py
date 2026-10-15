from dataclasses import dataclass

from common.response.domain import BaseResponseData
from security.models import SecurityEvent


@dataclass(frozen=True)
class SecurityEventData(BaseResponseData):
    event: SecurityEvent

    def to_dict(self) -> dict:
        event = self.event
        return {
            "id": str(event.pk),
            "event_type": event.event_type,
            "ip": event.ip,
            "user_agent": event.user_agent,
            "device_name": event.device_name,
            "metadata": event.metadata,
            "created_at": event.created_at.isoformat(),
        }
