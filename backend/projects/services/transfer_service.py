from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from accounts.models import User
from accounts.services import reauth_service
from accounts.services.reauth_service import Reauth
from common.exception.domain import ConflictException, NotFoundException
from projects import permissions
from projects.constants import actions, error_codes, limits, messages
from projects.constants.statuses import TransferStatus
from projects.models import Membership, OwnershipTransfer
from projects.services import (
    access,
    activity,
    email_service,
    grant_service,
)


def _expire_stale(**filters) -> int:
    return OwnershipTransfer.objects.filter(
        status=TransferStatus.PENDING, expires_at__lte=timezone.now(), **filters
    ).update(status=TransferStatus.EXPIRED)


def pending_for_project(project) -> OwnershipTransfer | None:
    return (
        OwnershipTransfer.objects.filter(
            project=project,
            status=TransferStatus.PENDING,
            expires_at__gt=timezone.now(),
        )
        .select_related("to_user")
        .first()
    )


def incoming(user: User) -> QuerySet[OwnershipTransfer]:
    return OwnershipTransfer.objects.filter(
        to_user=user,
        status=TransferStatus.PENDING,
        expires_at__gt=timezone.now(),
        project__is_deleted=False,
    ).select_related("project", "from_user", "to_user")


@transaction.atomic
def start(
    membership: Membership,
    to_user_id: UUID,
    reauth: Reauth,
    ip: str | None = None,
    verifier=None,
) -> OwnershipTransfer:
    permissions.require_owner(membership)
    project = membership.project
    access.ensure_not_demo(project)
    access.ensure_writable(project)
    reauth_service.confirm(membership.user, reauth, verifier)
    target = (
        Membership.objects.select_related("user")
        .filter(project=project, user_id=to_user_id, is_owner=False)
        .first()
    )
    if target is None:
        raise ConflictException(
            messages.INVALID_TRANSFER_TARGET,
            error_code=error_codes.INVALID_TRANSFER_TARGET,
        )
    _expire_stale(project=project)
    if OwnershipTransfer.objects.filter(
        project=project, status=TransferStatus.PENDING
    ).exists():
        raise ConflictException(
            messages.TRANSFER_PENDING, error_code=error_codes.TRANSFER_PENDING
        )
    transfer = OwnershipTransfer.objects.create(
        project=project,
        from_user=membership.user,
        to_user=target.user,
        expires_at=timezone.now() + timedelta(days=limits.TRANSFER_EXPIRY_DAYS),
    )
    activity.log(
        project,
        membership.user,
        actions.TRANSFER_STARTED,
        actions.ENTITY_TRANSFER,
        transfer.pk,
        {"to_user": str(target.user_id)},
        ip,
    )
    email_service.send_transfer_offer_email(project, membership.user, target.user)
    return transfer


@transaction.atomic
def cancel(membership: Membership, ip: str | None = None) -> OwnershipTransfer:
    permissions.require_owner(membership)
    transfer = pending_for_project(membership.project)
    if transfer is None:
        raise NotFoundException(
            messages.TRANSFER_NOT_FOUND, error_code=error_codes.TRANSFER_NOT_FOUND
        )
    transfer.status = TransferStatus.CANCELLED
    transfer.save(update_fields=["status", "updated_at"])
    activity.log(
        membership.project,
        membership.user,
        actions.TRANSFER_CANCELLED,
        actions.ENTITY_TRANSFER,
        transfer.pk,
        ip=ip,
    )
    return transfer


@transaction.atomic
def accept(user: User, transfer_id: UUID, ip: str | None = None) -> OwnershipTransfer:
    transfer = (
        OwnershipTransfer.objects.select_for_update(of=("self",))
        .select_related("project", "from_user", "to_user")
        .filter(pk=transfer_id, to_user=user, project__is_deleted=False)
        .first()
    )
    if transfer is None:
        raise NotFoundException(
            messages.TRANSFER_NOT_FOUND, error_code=error_codes.TRANSFER_NOT_FOUND
        )
    if transfer.status != TransferStatus.PENDING:
        raise ConflictException(
            messages.TRANSFER_NOT_PENDING, error_code=error_codes.TRANSFER_NOT_PENDING
        )
    if transfer.expires_at <= timezone.now():
        transfer.status = TransferStatus.EXPIRED
        transfer.save(update_fields=["status", "updated_at"])
        raise ConflictException(
            messages.TRANSFER_EXPIRED, error_code=error_codes.TRANSFER_EXPIRED
        )
    project = transfer.project
    access.ensure_writable(project)
    new_owner = Membership.objects.filter(project=project, user=user).first()
    old_owner = Membership.objects.filter(
        project=project, user=transfer.from_user, is_owner=True
    ).first()
    if new_owner is None or old_owner is None:
        raise ConflictException(
            messages.INVALID_TRANSFER_TARGET,
            error_code=error_codes.INVALID_TRANSFER_TARGET,
        )
    # The owner holds everything implicitly and the old owner starts with
    # nothing, so neither keeps stored grants.
    grant_service.clear_grants(new_owner, old_owner)
    # Clear the old flag first: only one owner row may exist at any moment.
    old_owner.is_owner = False
    old_owner.save(update_fields=["is_owner", "updated_at"])
    new_owner.is_owner = True
    new_owner.save(update_fields=["is_owner", "updated_at"])
    project.owner = user
    project.save(update_fields=["owner", "updated_at"])
    transfer.status = TransferStatus.ACCEPTED
    transfer.save(update_fields=["status", "updated_at"])
    activity.log(
        project,
        user,
        actions.TRANSFER_ACCEPTED,
        actions.ENTITY_TRANSFER,
        transfer.pk,
        {"from": str(transfer.from_user_id), "to": str(user.pk)},
        ip,
    )
    email_service.send_transfer_accepted_email(project, transfer.from_user, user)
    return transfer


def expire_transfers() -> int:
    return _expire_stale()
