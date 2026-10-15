from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from accounts.constants import error_codes, messages
from common.exception.domain import PermissionDeniedException


class IsProfileComplete(BasePermission):
    """Default permission. Authenticated, not pending deletion, and with a
    complete profile (Google may not return first and last name)."""

    def has_permission(self, request: Request, view: object) -> bool:
        user = request.user
        if not (user and user.is_authenticated) or user.is_system:
            return False
        if user.is_deleted:
            raise PermissionDeniedException(
                messages.ACCOUNT_PENDING_DELETION,
                error_code=error_codes.ACCOUNT_PENDING_DELETION,
            )
        if not user.is_profile_complete:
            raise PermissionDeniedException(
                messages.PROFILE_INCOMPLETE,
                error_code=error_codes.PROFILE_INCOMPLETE,
            )
        return True
