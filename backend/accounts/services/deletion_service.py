from collections.abc import Callable
from datetime import timedelta

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

from accounts.constants import error_codes, messages
from accounts.models import User
from common.exception.domain import ConflictException
from common.storage import get_storage
from security.constants.events import EventType
from security.services import event_service

# Features register a callable returning True when the user still owns
# something that blocks deletion (feature 2 registers "owns a project").
OwnershipCheck = Callable[[User], bool]
ownership_checks: list[OwnershipCheck] = []


def start_deletion(user: User, request: HttpRequest | None = None) -> User:
    if any(check(user) for check in list(ownership_checks)):
        raise ConflictException(
            messages.OWNS_PROJECTS,
            error_code=error_codes.OWNS_PROJECTS,
        )
    if not user.is_deleted:
        user.delete()  # soft delete: starts the grace period
        event_service.record(request, user, EventType.ACCOUNT_DELETION_REQUESTED)
    return user


def cancel_deletion(user: User, request: HttpRequest | None = None) -> User:
    if user.is_deleted:
        event_service.record(request, user, EventType.ACCOUNT_DELETION_CANCELLED)
        user.is_deleted = False
        user.deleted_at = None
        user.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    return user


def scheduled_purge_at(user: User):
    if not user.is_deleted or user.deleted_at is None:
        return None
    return user.deleted_at + timedelta(days=settings.ACCOUNT_DELETION_GRACE_DAYS)


def purge_expired_accounts() -> int:
    """Hard delete accounts whose grace period is over."""
    cutoff = timezone.now() - timedelta(days=settings.ACCOUNT_DELETION_GRACE_DAYS)
    expired = list(
        User.objects.filter(is_deleted=True, deleted_at__lt=cutoff, is_system=False)
    )
    storage = get_storage()
    for user in expired:
        if user.avatar:
            storage.delete(user.avatar)
    # UserManager returns a plain queryset, so this really deletes the rows.
    User.objects.filter(pk__in=[user.pk for user in expired]).delete()
    return len(expired)
