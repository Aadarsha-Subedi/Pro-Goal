"""What may be attached: sniffed MIME type -> (category, max file size)."""

from django.db import models

MB = 1024 * 1024


class Category(models.TextChoices):
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"


class Status(models.TextChoices):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"


class TargetType(models.TextChoices):
    TASK = "task"
    NOTE = "note"
    COMMENT = "comment"


CATEGORY_MAX_BYTES = {
    Category.IMAGE: 5 * MB,
    Category.DOCUMENT: 10 * MB,
    Category.AUDIO: 20 * MB,
}

ALLOWED_TYPES: dict[str, Category] = {
    "image/jpeg": Category.IMAGE,
    "image/png": Category.IMAGE,
    "image/webp": Category.IMAGE,
    "image/gif": Category.IMAGE,
    "application/pdf": Category.DOCUMENT,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": Category.DOCUMENT,
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": Category.DOCUMENT,
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": Category.DOCUMENT,
    "text/plain": Category.DOCUMENT,
    "audio/mpeg": Category.AUDIO,
    "audio/mp4": Category.AUDIO,
    "audio/x-m4a": Category.AUDIO,
}

# Types the browser may declare that are checked as plain text, not by magic bytes.
TEXT_TYPE = "text/plain"
# Images that a Celery task decodes and re-encodes to drop EXIF/location data.
REENCODED_IMAGE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
# Only these are ever served inline; everything else is a forced download.
INLINE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})
SNIFF_BYTES = 16 * 1024
