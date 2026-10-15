import codecs

import filetype

from attachments.constants import error_codes, messages
from attachments.constants.types import (
    ALLOWED_TYPES,
    CATEGORY_MAX_BYTES,
    TEXT_TYPE,
    Category,
)
from common.exception.domain import ValidationException

# Browsers and libraries name the same audio type differently.
_ALIASES = {"audio/x-m4a": "audio/mp4"}


def normalize_declared(content_type: str) -> str:
    return content_type.split(";")[0].strip().lower()


def _canonical(mime: str) -> str:
    return _ALIASES.get(mime, mime)


def category_for(mime: str) -> Category | None:
    return ALLOWED_TYPES.get(mime)


def max_bytes(category: Category) -> int:
    return CATEGORY_MAX_BYTES[category]


def _rejected() -> ValidationException:
    return ValidationException(
        messages.TYPE_NOT_ALLOWED, error_code=error_codes.TYPE_NOT_ALLOWED
    )


def check_declared(content_type: str, size: int) -> tuple[str, Category]:
    """Early check from what the browser says it will upload."""
    declared = normalize_declared(content_type)
    category = category_for(declared)
    if category is None:
        raise _rejected()
    if size <= 0:
        raise ValidationException(
            messages.EMPTY_FILE, error_code=error_codes.EMPTY_FILE
        )
    if size > max_bytes(category):
        raise _too_large(category)
    return declared, category


def _too_large(category: Category) -> ValidationException:
    return ValidationException(
        messages.FILE_TOO_LARGE.format(limit=max_bytes(category) // (1024 * 1024)),
        error_code=error_codes.FILE_TOO_LARGE,
    )


def _looks_like_text(head: bytes) -> bool:
    if b"\x00" in head:
        return False
    try:
        # final=False tolerates a multi-byte character cut by the sniff window.
        codecs.getincrementaldecoder("utf-8")().decode(head, final=False)
    except UnicodeDecodeError:
        return False
    return True


def sniff(head: bytes, declared: str, size: int) -> tuple[str, Category]:
    """Decide the real type from the file's bytes. It must match what was
    declared (and signed), otherwise the file is refused."""
    if declared == TEXT_TYPE:
        # Plain text has no signature: it must be UTF-8 text and not any
        # recognisable binary format.
        if filetype.guess(head) is not None or not _looks_like_text(head):
            raise _rejected()
        mime = TEXT_TYPE
    else:
        guessed = filetype.guess(head)
        if guessed is None or _canonical(guessed.mime) != _canonical(declared):
            raise _rejected()
        mime = declared
    category = category_for(mime)
    if category is None:
        raise _rejected()
    if size > max_bytes(category):
        raise _too_large(category)
    return mime, category
