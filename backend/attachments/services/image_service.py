from io import BytesIO
from uuid import UUID

from django.utils import timezone
from PIL import Image, ImageOps, UnidentifiedImageError

from attachments.constants import limits
from attachments.constants.types import REENCODED_IMAGE_FORMATS, Status
from attachments.models import Attachment
from attachments.services import quota_service
from attachments.services.storage import storage

_SAVE_OPTIONS = {
    "JPEG": {"quality": 90, "optimize": True},
    "PNG": {"optimize": True},
    "WEBP": {"quality": 90},
}


def _reencode(data: bytes, expected_format: str) -> bytes:
    """Decode and re-save the pixels. Metadata such as EXIF and GPS does not
    survive; orientation is applied first so the picture still looks right."""
    Image.MAX_IMAGE_PIXELS = limits.MAX_IMAGE_PIXELS
    with Image.open(BytesIO(data)) as probe:
        if probe.format != expected_format:
            raise ValueError("format changed")
        probe.verify()
    with Image.open(BytesIO(data)) as image:
        image.load()
        image = ImageOps.exif_transpose(image)
        if expected_format == "JPEG" and image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        out = BytesIO()
        image.save(out, format=expected_format, **_SAVE_OPTIONS[expected_format])
        return out.getvalue()


def process(attachment_id: UUID | str) -> Attachment | None:
    """Re-encode a confirmed image and mark it ready. A file that cannot be
    decoded is deleted, which frees its quota."""
    attachment = Attachment.objects.filter(
        pk=attachment_id, status=Status.PROCESSING
    ).first()
    if attachment is None:
        return None
    expected = REENCODED_IMAGE_FORMATS.get(attachment.content_type)
    store = storage()
    try:
        data = _reencode(store.read(attachment.object_key), expected)
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        SyntaxError,
        Image.DecompressionBombError,
    ):
        attachment.delete()
        return None

    store.upload(attachment.object_key, data, attachment.content_type)
    delta = len(data) - attachment.size_bytes
    attachment.size_bytes = len(data)
    attachment.status = Status.READY
    attachment.updated_at = timezone.now()
    attachment.save(update_fields=["size_bytes", "status", "updated_at"])
    if delta:
        quota_service.adjust(attachment.project_id, attachment.uploaded_by_id, delta)
    return attachment
