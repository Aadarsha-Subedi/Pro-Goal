from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from attachments.models import Attachment
from common.response.domain import BaseResponseData
from tracker.responses import user_or_deleted


@dataclass(frozen=True)
class AttachmentData(BaseResponseData):
    attachment: Attachment

    def to_dict(self) -> dict:
        item = self.attachment
        if item.task_id:
            target = {"type": "task", "id": str(item.task_id)}
        elif item.note_id:
            target = {"type": "note", "id": str(item.note_id)}
        else:
            target = {"type": "comment", "id": str(item.comment_id)}
        return {
            "id": str(item.pk),
            "filename": item.filename,
            "content_type": item.content_type,
            "category": item.category,
            "size_bytes": item.size_bytes,
            "status": item.status,
            "target": target,
            "uploaded_by": user_or_deleted(item.uploaded_by),
            "created_at": item.created_at.isoformat(),
        }


@dataclass(frozen=True)
class UploadData(BaseResponseData):
    """The pending attachment plus how to upload the file."""

    attachment: Attachment
    url: str
    expires_in: int

    def to_dict(self) -> dict:
        expires_at = timezone.now() + timedelta(seconds=self.expires_in)
        return {
            "attachment": AttachmentData(self.attachment).to_dict(),
            "upload": {
                "method": "PUT",
                "url": self.url,
                "headers": {"Content-Type": self.attachment.content_type},
                "expires_at": expires_at.isoformat(),
            },
        }


@dataclass(frozen=True)
class DownloadData(BaseResponseData):
    url: str
    expires_in: int

    def to_dict(self) -> dict:
        expires_at = timezone.now() + timedelta(seconds=self.expires_in)
        return {"url": self.url, "expires_at": expires_at.isoformat()}


@dataclass(frozen=True)
class UsageData(BaseResponseData):
    usage: dict

    def to_dict(self) -> dict:
        return self.usage
