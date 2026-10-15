import re
import unicodedata
from datetime import timedelta
from uuid import UUID, uuid7

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from attachments.constants import actions, error_codes, limits, messages
from attachments.constants.types import (
    INLINE_TYPES,
    REENCODED_IMAGE_FORMATS,
    SNIFF_BYTES,
    Status,
    TargetType,
)
from attachments.models import Attachment
from attachments.services import quota_service, type_rules
from attachments.services.storage import (
    DirectUploadUnsupported,
    not_configured,
    storage,
)
from common.exception.domain import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from projects import permissions
from projects.constants import permissions as codes
from projects.models import Membership
from projects.services import access as project_access
from projects.services import activity
from tracker.models import Comment, Note, Task

_PATH_CHARS = re.compile(r"[\\/\x00-\x1f\x7f]")


def sanitize_filename(name: str) -> str:
    """Keep only the file's own name: no directories, no control characters."""
    name = unicodedata.normalize("NFC", name)
    name = _PATH_CHARS.sub("_", name).strip().strip(".")
    name = name[-limits.FILENAME_MAX_LENGTH :]
    return name or "file"


def _not_found(message: str, code: str) -> NotFoundException:
    return NotFoundException(message, error_code=code)


def resolve_target(
    membership: Membership, target_type: str, target: str | int | UUID
) -> Task | Note | Comment:
    project = membership.project
    found = None
    if target_type == TargetType.TASK:
        found = Task.objects.filter(project=project, number=target).first()
    elif target_type == TargetType.NOTE:
        found = Note.objects.filter(project=project, pk=target).first()
    elif target_type == TargetType.COMMENT:
        found = Comment.objects.filter(task__project=project, pk=target).first()
    if found is None:
        raise _not_found(messages.TARGET_NOT_FOUND, error_codes.TARGET_NOT_FOUND)
    return found


def _target_fields(target: Task | Note | Comment) -> dict:
    return {target.__class__.__name__.lower(): target}


def get_attachment(membership: Membership, attachment_id: UUID) -> Attachment:
    attachment = Attachment.objects.filter(
        project=membership.project, pk=attachment_id
    ).first()
    if attachment is None:
        raise _not_found(
            messages.ATTACHMENT_NOT_FOUND, error_codes.ATTACHMENT_NOT_FOUND
        )
    return attachment


def request_upload(
    membership: Membership,
    *,
    target_type: str,
    target: str | int | UUID,
    filename: str,
    content_type: str,
    size: int,
) -> tuple[Attachment, str, int]:
    """Check everything, reserve the quota and return the pending attachment
    with the signed PUT URL and its lifetime in seconds."""
    permissions.require_permission(membership, codes.ATTACHMENT_CREATE)
    project = membership.project
    project_access.ensure_writable(project)
    declared, category = type_rules.check_declared(content_type, size)
    parent = resolve_target(membership, target_type, target)
    fields = _target_fields(parent)
    if Attachment.objects.filter(**fields).count() >= limits.MAX_ATTACHMENTS_PER_TARGET:
        raise ConflictException(
            messages.TARGET_FULL.format(limit=limits.MAX_ATTACHMENTS_PER_TARGET),
            error_code=error_codes.TARGET_FULL,
        )

    attachment_id = uuid7()
    key = limits.OBJECT_KEY.format(project_id=project.pk, attachment_id=attachment_id)
    with transaction.atomic():
        quota_service.reserve(project.pk, membership.user_id, size)
        attachment = Attachment.objects.create(
            id=attachment_id,
            project=project,
            uploaded_by=membership.user,
            object_key=key,
            filename=sanitize_filename(filename),
            content_type=declared,
            category=category,
            size_bytes=size,
            status=Status.PENDING,
            **fields,
        )
        try:
            url = storage().presign_put(
                key, declared, size, limits.UPLOAD_URL_TTL_SECONDS
            )
        except DirectUploadUnsupported:
            raise not_configured() from None
    return attachment, url, limits.UPLOAD_URL_TTL_SECONDS


def _discard(attachment: Attachment) -> None:
    # The post_delete signal frees the quota and removes the R2 object. This
    # runs outside any transaction, so a refused file stays deleted even
    # though the request then fails.
    attachment.delete()


def confirm(
    membership: Membership, attachment_id: UUID, ip: str | None = None
) -> Attachment:
    attachment = get_attachment(membership, attachment_id)
    if attachment.uploaded_by_id != membership.user_id:
        raise _not_found(
            messages.ATTACHMENT_NOT_FOUND, error_codes.ATTACHMENT_NOT_FOUND
        )
    if attachment.status != Status.PENDING:
        return attachment  # confirming twice is harmless

    store = storage()
    info = store.head(attachment.object_key)
    if info is None:
        raise ValidationException(
            messages.UPLOAD_MISSING, error_code=error_codes.UPLOAD_MISSING
        )
    if info.size != attachment.size_bytes:
        _discard(attachment)
        raise ValidationException(
            messages.UPLOAD_SIZE_MISMATCH, error_code=error_codes.UPLOAD_SIZE_MISMATCH
        )
    head = store.read_range(attachment.object_key, SNIFF_BYTES)
    try:
        mime, category = type_rules.sniff(
            head, attachment.content_type, attachment.size_bytes
        )
    except ValidationException:
        _discard(attachment)
        raise

    reencode = mime in REENCODED_IMAGE_FORMATS
    with transaction.atomic():
        attachment.content_type = mime
        attachment.category = category
        attachment.status = Status.PROCESSING if reencode else Status.READY
        attachment.save(
            update_fields=["content_type", "category", "status", "updated_at"]
        )
        activity.log(
            membership.project,
            membership.user,
            actions.ATTACHMENT_ADDED,
            actions.ENTITY_ATTACHMENT,
            attachment.pk,
            {"filename": attachment.filename, "size": attachment.size_bytes},
            ip,
        )
        if reencode:
            from attachments.tasks import process_image

            transaction.on_commit(lambda: process_image.delay(str(attachment.pk)))
    return attachment


def download_url(membership: Membership, attachment_id: UUID) -> tuple[str, int]:
    attachment = get_attachment(membership, attachment_id)
    if attachment.status != Status.READY:
        raise ConflictException(messages.NOT_READY, error_code=error_codes.NOT_READY)
    inline = attachment.content_type in INLINE_TYPES
    url = storage().presign_get(
        attachment.object_key,
        limits.DOWNLOAD_URL_TTL_SECONDS,
        filename=attachment.filename,
        inline=inline,
    )
    return url, limits.DOWNLOAD_URL_TTL_SECONDS


@transaction.atomic
def delete(membership: Membership, attachment_id: UUID, ip: str | None = None) -> None:
    attachment = get_attachment(membership, attachment_id)
    permissions.require_permission_or_own(
        membership, codes.ATTACHMENT_DELETE, attachment.uploaded_by_id
    )
    project_access.ensure_writable(membership.project)
    activity.log(
        membership.project,
        membership.user,
        actions.ATTACHMENT_DELETED,
        actions.ENTITY_ATTACHMENT,
        attachment.pk,
        {"filename": attachment.filename},
        ip,
    )
    attachment.delete()


def list_for_target(
    membership: Membership,
    *,
    target_type: str | None = None,
    target: str | int | UUID | None = None,
) -> QuerySet[Attachment]:
    queryset = Attachment.objects.filter(
        project=membership.project, status__in=[Status.PROCESSING, Status.READY]
    ).select_related("uploaded_by")
    if target_type is None:
        return queryset
    parent = resolve_target(membership, target_type, target)
    return queryset.filter(**_target_fields(parent))


def cleanup_pending() -> int:
    """Delete uploads that were never confirmed (their quota comes back)."""
    cutoff = timezone.now() - timedelta(hours=limits.PENDING_MAX_AGE_HOURS)
    stale = list(
        Attachment.objects.filter(status=Status.PENDING, created_at__lt=cutoff)
    )
    for attachment in stale:
        attachment.delete()
    return len(stale)
