from uuid import UUID

from django.db import transaction
from django.db.models import Q, QuerySet

from accounts.models import User
from common.exception.domain import ConflictException, NotFoundException
from projects import permissions
from projects.constants import actions, error_codes, messages
from projects.constants.permissions import MEMBER_REMOVE
from projects.models import Membership
from projects.services import access, activity, email_service
from projects.services.reassignment import registry


def list_members(membership: Membership) -> QuerySet[Membership]:
    """Members of the project. In a demo project everyone is a stranger, so
    only the owner and the caller are listed."""
    queryset = Membership.objects.filter(project=membership.project)
    if membership.project.is_demo:
        queryset = queryset.filter(Q(is_owner=True) | Q(pk=membership.pk))
    return queryset.select_related("user").order_by("-is_owner", "joined_at")


@transaction.atomic
def remove(
    membership: Membership,
    target_user_id: UUID,
    reassign: dict[str, UUID] | None = None,
    ip: str | None = None,
) -> None:
    permissions.require_permission(membership, MEMBER_REMOVE)
    project = membership.project
    access.ensure_writable(project)
    target = (
        Membership.objects.select_related("user")
        .filter(project=project, user_id=target_user_id)
        .first()
    )
    if target is None:
        raise NotFoundException(
            messages.MEMBER_NOT_FOUND, error_code=error_codes.MEMBER_NOT_FOUND
        )
    if target.is_owner:
        raise ConflictException(
            messages.CANNOT_REMOVE_OWNER, error_code=error_codes.CANNOT_REMOVE_OWNER
        )
    if target.user_id == membership.user_id:
        raise ConflictException(
            messages.CANNOT_REMOVE_SELF, error_code=error_codes.CANNOT_REMOVE_SELF
        )
    _detach(target, reassign)
    activity.log(
        project,
        membership.user,
        actions.MEMBER_REMOVED,
        actions.ENTITY_MEMBER,
        target.user_id,
        {"reassign": {k: str(v) for k, v in (reassign or {}).items()}},
        ip,
    )
    email_service.send_member_removed_email(project, target.user)


@transaction.atomic
def leave(membership: Membership, ip: str | None = None) -> None:
    if membership.is_owner:
        raise ConflictException(
            messages.OWNER_CANNOT_LEAVE, error_code=error_codes.OWNER_CANNOT_LEAVE
        )
    _detach(membership, None)
    activity.log(
        membership.project,
        membership.user,
        actions.MEMBER_LEFT,
        actions.ENTITY_MEMBER,
        membership.user_id,
        ip=ip,
    )


def _detach(target: Membership, reassign: dict[str, UUID] | None) -> None:
    """Move everything the member owned, then drop the membership. Items not in
    the map become unassigned."""
    user: User = target.user
    registry.run(target.project, user, reassign)
    target.delete()
