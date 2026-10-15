from uuid import UUID

from django.db import transaction

from common.exception.domain import (
    ConflictException,
    NotFoundException,
    PermissionDeniedException,
    ValidationException,
)
from projects import permissions
from projects.constants import actions, error_codes, messages
from projects.constants.permissions import (
    PERMISSIONS_MANAGE,
    PRESETS,
    REGISTERED,
)
from projects.models import MemberPermission, Membership
from projects.services import access, activity


def resolve(
    codes: list[str] | None = None, preset: str | None = None
) -> set[str] | None:
    """The set of codes asked for (None when nothing was asked), validated
    against the registry. A preset name expands to its codes."""
    if preset is not None:
        found = PRESETS.get(preset)
        if found is None:
            raise ValidationException(
                errors=[
                    {
                        "field": "preset",
                        "message": messages.UNKNOWN_PRESET.format(name=preset),
                    }
                ],
                error_code=error_codes.UNKNOWN_PRESET,
            )
        return set(found.codes)
    if codes is None:
        return None
    unknown = sorted(set(codes) - REGISTERED)
    if unknown:
        raise ValidationException(
            errors=[
                {
                    "field": "permissions",
                    "message": messages.UNKNOWN_PERMISSION.format(code=code),
                }
                for code in unknown
            ],
            error_code=error_codes.UNKNOWN_PERMISSION,
        )
    return set(codes)


def preset_name_for(codes: set[str] | frozenset[str]) -> str | None:
    for name, preset in PRESETS.items():
        if set(preset.codes) == set(codes):
            return name
    return None


def _target(actor: Membership, user_id: UUID, *, lock: bool = False) -> Membership:
    queryset = Membership.objects.select_related("user").filter(
        project=actor.project, user_id=user_id
    )
    if lock:
        queryset = queryset.select_for_update(of=("self",))
    target = queryset.first()
    if target is None:
        raise NotFoundException(
            messages.MEMBER_NOT_FOUND, error_code=error_codes.MEMBER_NOT_FOUND
        )
    return target


def _require_subset(actor: Membership, changed: set[str]) -> None:
    """A delegate can only hand out or take back what they hold themselves."""
    missing = sorted(changed - permissions.held_codes(actor))
    if missing:
        raise PermissionDeniedException(
            messages.CANNOT_GRANT_PERMISSION.format(codes=", ".join(missing)),
            errors=[
                {"field": "permissions", "message": code, "code": code}
                for code in missing
            ],
            error_code=error_codes.CANNOT_GRANT_PERMISSION,
        )


def read(actor: Membership, user_id: UUID) -> tuple[Membership, list[str]]:
    """A member's grants. Visible to the owner, to anyone who manages
    permissions, and to the member themselves."""
    if actor.user_id != user_id:
        permissions.require_permission(actor, PERMISSIONS_MANAGE)
    target = _target(actor, user_id)
    return target, permissions.permissions_for(target)


@transaction.atomic
def replace(
    actor: Membership, user_id: UUID, wanted: set[str], ip: str | None = None
) -> tuple[Membership, list[str]]:
    """Make the member's grants equal `wanted`. Only the difference is checked
    against what the actor holds."""
    permissions.require_permission(actor, PERMISSIONS_MANAGE)
    access.ensure_not_demo(actor.project)
    access.ensure_writable(actor.project)
    target = _target(actor, user_id, lock=True)
    if target.is_owner:
        raise ConflictException(
            messages.CANNOT_MANAGE_OWNER, error_code=error_codes.CANNOT_MANAGE_OWNER
        )
    current = set(
        MemberPermission.objects.filter(membership=target).values_list(
            "code", flat=True
        )
    )
    added, removed = wanted - current, current - wanted
    _require_subset(actor, added | removed)

    MemberPermission.objects.filter(membership=target, code__in=removed).delete()
    MemberPermission.objects.bulk_create(
        MemberPermission(membership=target, code=code, granted_by=actor.user)
        for code in sorted(added)
    )
    permissions.invalidate_grants(target)
    if target.user_id == actor.user_id:
        permissions.invalidate_grants(actor)
    if added or removed:
        activity.log(
            actor.project,
            actor.user,
            actions.PERMISSIONS_CHANGED,
            actions.ENTITY_MEMBER,
            target.user_id,
            {"added": sorted(added), "removed": sorted(removed)},
            ip,
        )
    return target, permissions.permissions_for(target)


def check_starting_grants(actor: Membership, wanted: set[str] | None) -> set[str]:
    """Validate permissions chosen while approving a join request. Choosing
    any needs `permissions.manage` and the same subset rule; the default is
    none. Runs before the request is approved so a refusal changes nothing."""
    if not wanted:
        return set()
    permissions.require_permission(actor, PERMISSIONS_MANAGE)
    _require_subset(actor, wanted)
    return wanted


def give_starting_grants(
    target: Membership, granted_by: Membership, codes: set[str]
) -> None:
    MemberPermission.objects.bulk_create(
        MemberPermission(membership=target, code=code, granted_by=granted_by.user)
        for code in sorted(codes)
    )


def clear_grants(*memberships: Membership) -> None:
    MemberPermission.objects.filter(membership__in=memberships).delete()
    for membership in memberships:
        permissions.invalidate_grants(membership)
