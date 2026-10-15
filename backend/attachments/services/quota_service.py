from django.db import transaction
from django.db.models import F, Sum
from django.db.models.functions import Greatest

from accounts.models import User
from attachments.constants import error_codes, messages
from attachments.models import Attachment, ProjectStorageUsage, UserStorageUsage
from common.exception.domain import ConflictException
from projects.models import Project


def _ensure_rows(project_id, user_id) -> None:
    ProjectStorageUsage.objects.get_or_create(project_id=project_id)
    if user_id is not None:
        UserStorageUsage.objects.get_or_create(user_id=user_id)


@transaction.atomic
def reserve(project_id, user_id, size: int) -> None:
    """Add `size` to the user's and the project's counters, or refuse. The
    conditional UPDATE is the check, so parallel requests cannot both slip
    under a limit."""
    _ensure_rows(project_id, user_id)
    user_rows = UserStorageUsage.objects.filter(
        user_id=user_id, bytes_used__lte=F("quota_bytes") - size
    ).update(bytes_used=F("bytes_used") + size)
    if not user_rows:
        raise ConflictException(
            messages.USER_QUOTA_EXCEEDED, error_code=error_codes.USER_QUOTA_EXCEEDED
        )
    project_rows = ProjectStorageUsage.objects.filter(
        project_id=project_id, bytes_used__lte=F("quota_bytes") - size
    ).update(bytes_used=F("bytes_used") + size)
    if not project_rows:
        # Roll back the user increment too.
        transaction.set_rollback(True)
        raise ConflictException(
            messages.PROJECT_QUOTA_EXCEEDED,
            error_code=error_codes.PROJECT_QUOTA_EXCEEDED,
        )


def release(project_id, user_id, size: int) -> None:
    adjust(project_id, user_id, -size)


def adjust(project_id, user_id, delta: int) -> None:
    """Change both counters by `delta` (never below zero)."""
    ProjectStorageUsage.objects.filter(project_id=project_id).update(
        bytes_used=Greatest(F("bytes_used") + delta, 0)
    )
    if user_id is not None:
        UserStorageUsage.objects.filter(user_id=user_id).update(
            bytes_used=Greatest(F("bytes_used") + delta, 0)
        )


def project_usage(project: Project) -> dict:
    usage, _ = ProjectStorageUsage.objects.get_or_create(project=project)
    rows = Attachment.objects.filter(project=project)
    by_category = {
        row["category"]: row["total"]
        for row in rows.values("category").annotate(total=Sum("size_bytes"))
    }
    by_uploader = [
        {
            "user_id": str(row["uploaded_by"]) if row["uploaded_by"] else None,
            "first_name": row["uploaded_by__first_name"] or "Deleted user",
            "bytes": row["total"],
        }
        for row in rows.values("uploaded_by", "uploaded_by__first_name")
        .annotate(total=Sum("size_bytes"))
        .order_by("-total")
    ]
    return {
        "bytes_used": usage.bytes_used,
        "quota_bytes": usage.quota_bytes,
        "by_category": by_category,
        "by_uploader": by_uploader,
    }


def user_usage(user: User) -> dict:
    usage, _ = UserStorageUsage.objects.get_or_create(user=user)
    by_project = [
        {
            "project_id": str(row["project"]),
            "project_name": row["project__name"],
            "bytes": row["total"],
        }
        for row in Attachment.objects.filter(uploaded_by=user)
        .values("project", "project__name")
        .annotate(total=Sum("size_bytes"))
        .order_by("-total")
    ]
    return {
        "bytes_used": usage.bytes_used,
        "quota_bytes": usage.quota_bytes,
        "by_project": by_project,
    }


def recompute_project(project_id) -> int:
    total = (
        Attachment.objects.filter(project_id=project_id).aggregate(t=Sum("size_bytes"))[
            "t"
        ]
        or 0
    )
    ProjectStorageUsage.objects.update_or_create(
        project_id=project_id, defaults={"bytes_used": total}
    )
    return total


def recompute_user(user_id) -> int:
    total = (
        Attachment.objects.filter(uploaded_by_id=user_id).aggregate(
            t=Sum("size_bytes")
        )["t"]
        or 0
    )
    UserStorageUsage.objects.update_or_create(
        user_id=user_id, defaults={"bytes_used": total}
    )
    return total
