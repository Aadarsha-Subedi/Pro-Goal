from dataclasses import dataclass

from common.response.domain import BaseResponseData
from integrations.models import SlackChannelMapping


@dataclass(frozen=True)
class UrlData(BaseResponseData):
    url: str
    extra: dict | None = None

    def to_dict(self) -> dict:
        return {"url": self.url, **(self.extra or {})}


@dataclass(frozen=True)
class ChannelData(BaseResponseData):
    channel: dict

    def to_dict(self) -> dict:
        return self.channel


@dataclass(frozen=True)
class MappingData(BaseResponseData):
    mapping: SlackChannelMapping

    def to_dict(self) -> dict:
        item = self.mapping
        return {
            "id": str(item.pk),
            "channel_id": item.channel_id,
            "channel_name": item.channel_name,
            "is_public": item.is_public,
            # Public channels may be seen by the whole workspace: warn in the UI.
            "warn_public": item.is_public,
            "enabled_events": item.enabled_events,
            "created_at": item.created_at.isoformat(),
        }


@dataclass(frozen=True)
class PreferenceData(BaseResponseData):
    preference: dict

    def to_dict(self) -> dict:
        return self.preference
