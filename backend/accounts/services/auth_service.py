from allauth.account.models import EmailAddress
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.http import HttpRequest

from accounts.constants import error_codes, messages
from accounts.models import User, UserSession
from accounts.services import deletion_service, session_service
from common.email.utils import normalize_email
from common.exception.domain import (
    AuthenticationDeniedException,
    PermissionDeniedException,
)
from security.services import lockout_service, login_monitor


def start_session(request: HttpRequest, user: User, remember_me: bool) -> None:
    """Log the user in, set the sliding lifetime and record a UserSession.
    Logging in during the deletion grace period cancels the deletion."""
    if user.is_system:
        raise AuthenticationDeniedException(
            messages.INVALID_CREDENTIALS, error_code=error_codes.INVALID_CREDENTIALS
        )
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    if remember_me:
        request.session.set_expiry(settings.SESSION_REMEMBER_ME_AGE)
    deletion_service.cancel_deletion(user, request)
    session_service.register_session(request, user, remember_me)
    login_monitor.on_login_success(request, user)


def log_in(
    request: HttpRequest, *, email: str, password: str, remember_me: bool
) -> User:
    email = normalize_email(email)
    lockout_service.check(email)
    user = authenticate(request, username=email, password=password)
    if user is None:
        login_monitor.on_login_failure(
            request, email, User.objects.filter(email__iexact=email).first()
        )
        raise AuthenticationDeniedException(
            messages.INVALID_CREDENTIALS, error_code=error_codes.INVALID_CREDENTIALS
        )

    if not EmailAddress.objects.filter(user=user, verified=True).exists():
        raise PermissionDeniedException(
            messages.EMAIL_NOT_VERIFIED,
            error_code=error_codes.EMAIL_NOT_VERIFIED,
        )

    start_session(request, user, remember_me)
    return user


def log_out(request: HttpRequest, *, all_other_sessions: bool = False) -> None:
    key = request.session.session_key
    user = request.user
    if all_other_sessions:
        session_service.revoke_all(user, except_key=key)
    if key:
        UserSession.objects.filter(session_key=key).delete()
    logout(request)  # flushes the Django session itself


def keep_current_session(request: HttpRequest, user: User) -> None:
    """After a password change: keep this session valid, revoke the rest.

    update_session_auth_hash cycles the session key, so the UserSession row
    must follow it or the current session would vanish from the session list.
    """
    old_key = request.session.session_key
    update_session_auth_hash(request, user)
    new_key = request.session.session_key
    if old_key and new_key and old_key != new_key:
        UserSession.objects.filter(session_key=old_key).update(session_key=new_key)
    session_service.revoke_all(user, except_key=new_key)
