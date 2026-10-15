"""Single place that decides who may do what in a project.

The owner holds every permission code implicitly. Any other member holds the
codes granted to them (`MemberPermission` rows), read from the database once
per request and cached on the `Membership` instance. Reading needs no code.
Owner-only actions (delete, transfer, archive, ...) use `require_owner`.
"""

from collections.abc import Iterable

from common.exception.domain import PermissionDeniedException
from projects.constants import error_codes, messages
from projects.constants.permissions import ALL_PERMISSIONS
from projects.models import MemberPermission, Membership

_CACHE_ATTR = "_grant_codes"


def held_codes(membership: Membership) -> frozenset[str]:
    """Every code this member holds, checked against the database at most once
    per `Membership` instance (instances live for one request)."""
    if membership.is_owner:
        return frozenset(ALL_PERMISSIONS)
    cached = getattr(membership, _CACHE_ATTR, None)
    if cached is None:
        cached = frozenset(
            MemberPermission.objects.filter(membership=membership).values_list(
                "code", flat=True
            )
        )
        setattr(membership, _CACHE_ATTR, cached)
    return cached


def invalidate_grants(membership: Membership) -> None:
    if hasattr(membership, _CACHE_ATTR):
        delattr(membership, _CACHE_ATTR)


def has_permission(membership: Membership, code: str) -> bool:
    return code in held_codes(membership)


def permissions_for(membership: Membership) -> list[str]:
    held = held_codes(membership)
    return [code for code in ALL_PERMISSIONS if code in held]


def _denied() -> PermissionDeniedException:
    return PermissionDeniedException(
        messages.PERMISSION_DENIED, error_code=error_codes.PERMISSION_DENIED
    )


def require_permission(membership: Membership, code: str) -> None:
    if not has_permission(membership, code):
        raise _denied()


def require_permission_or_own(
    membership: Membership, code: str, creator_id: object | None
) -> None:
    """For things anyone may remove without a grant when they made them
    (attachments): the grant holder, or the person who created it."""
    own = creator_id is not None and creator_id == membership.user_id
    if not (own or has_permission(membership, code)):
        raise _denied()


def require_owner(membership: Membership) -> None:
    if not membership.is_owner:
        raise PermissionDeniedException(
            messages.OWNER_ONLY, error_code=error_codes.OWNER_ONLY
        )


def require_fields(membership: Membership, field_codes: Iterable[tuple[str, str]]):
    """Raise one 403 listing every field the caller may not change."""
    forbidden = [f for f, code in field_codes if not has_permission(membership, code)]
    if forbidden:
        raise PermissionDeniedException(
            messages.FIELDS_FORBIDDEN.format(fields=", ".join(forbidden)),
            errors=[
                {"field": f, "message": messages.PERMISSION_DENIED} for f in forbidden
            ],
            error_code=error_codes.FIELDS_FORBIDDEN,
        )
