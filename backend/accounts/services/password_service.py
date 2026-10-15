from allauth.account.models import EmailAddress
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.http import HttpRequest
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from accounts.constants import error_codes, messages
from accounts.constants.cache import (
    PASSWORD_RESET_KEY,
    PASSWORD_RESET_WINDOW_SECONDS,
    RESET_REQUESTS_PER_HOUR,
)
from accounts.models import User
from accounts.services import auth_service, email_service, session_service
from common.email.utils import normalize_email
from common.exception.domain import (
    AuthenticationDeniedException,
    InvalidTokenException,
)
from common.validators.password import (
    validate_password_changed,
    validate_password_strength,
)
from security.constants.events import EventType
from security.services import event_service


def request_reset(email: str) -> None:
    """Neutral reply. Capped at 3 mails per hour per email address."""
    email = normalize_email(email)
    key = PASSWORD_RESET_KEY.format(email=email)
    cache.add(key, 0, PASSWORD_RESET_WINDOW_SECONDS)
    try:
        count = cache.incr(key)
    except ValueError:
        count = 1
    if count > RESET_REQUESTS_PER_HOUR:
        return

    user = User.objects.filter(
        email__iexact=email, is_active=True, is_system=False
    ).first()
    if user is None:
        return
    email_service.send_password_reset_email(
        user.email,
        urlsafe_base64_encode(force_bytes(str(user.pk))),
        default_token_generator.make_token(user),
    )


def confirm_reset(
    request: HttpRequest, *, uid: str, token: str, new_password: str
) -> User:
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except User.DoesNotExist, ValueError, TypeError, OverflowError:
        user = None
    if user is None or not default_token_generator.check_token(user, token):
        raise InvalidTokenException(
            messages.RESET_LINK_INVALID,
            error_code=error_codes.RESET_TOKEN_INVALID,
        )

    validate_password_strength(new_password, user, field="new_password")
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    # Following the emailed link proves the user controls the address.
    EmailAddress.objects.filter(user=user, email__iexact=user.email).update(
        verified=True
    )
    session_service.revoke_all(user)
    event_service.record(request, user, EventType.PASSWORD_RESET)
    # If this browser was logged in, its session was just revoked: drop the
    # local session state too, or the session middleware tries to re-save it.
    request.session.flush()
    email_service.send_password_changed_email(user.email)
    return user


def change_password(
    request: HttpRequest, user: User, *, current_password: str | None, new_password: str
) -> None:
    had_password = user.has_usable_password()
    if had_password and not (
        current_password and user.check_password(current_password)
    ):
        raise AuthenticationDeniedException(
            messages.CURRENT_PASSWORD_INCORRECT,
            error_code=error_codes.INVALID_CURRENT_PASSWORD,
        )
    validate_password_strength(new_password, user, field="new_password")
    if had_password:
        validate_password_changed(user, new_password)

    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    auth_service.keep_current_session(request, user)
    event_service.record(request, user, EventType.PASSWORD_CHANGED)
    email_service.send_password_changed_email(user.email)
