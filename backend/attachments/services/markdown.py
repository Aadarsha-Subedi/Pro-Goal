import re
from uuid import UUID

from attachments.constants import error_codes, messages
from attachments.constants.types import Status
from attachments.models import Attachment
from common.exception.domain import ValidationException
from projects.models import Project

# ![alt](target "title")
_IMAGE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+[\"'][^)]*[\"'])?\s*\)")
_REFERENCE_IMAGE = re.compile(r"!\[[^\]]*\]\[[^\]]*\]")
_HTML_IMG = re.compile(r"<\s*img\b", re.IGNORECASE)
_ATTACHMENT_URL = re.compile(
    r"^attachment:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})$"
)


def _invalid() -> ValidationException:
    return ValidationException(
        errors=[{"field": "body", "message": messages.INVALID_NOTE_IMAGE}],
        error_code=error_codes.INVALID_NOTE_IMAGE,
    )


def validate_note_images(project: Project, body: str) -> None:
    """Images in a note may only point at attachments of the same project
    (`attachment:<id>`): no external URLs, raw HTML images or reference-style
    images."""
    if _HTML_IMG.search(body) or _REFERENCE_IMAGE.search(body):
        raise _invalid()
    ids: set[UUID] = set()
    for target in _IMAGE.findall(body):
        match = _ATTACHMENT_URL.match(target)
        if match is None:
            raise _invalid()
        ids.add(UUID(match.group(1)))
    if not ids:
        return
    found = set(
        Attachment.objects.filter(
            project=project, pk__in=ids, status__in=[Status.PROCESSING, Status.READY]
        ).values_list("pk", flat=True)
    )
    if found != ids:
        raise _invalid()
