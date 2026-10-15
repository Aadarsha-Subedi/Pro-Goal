from allauth.account.models import EmailAddress
from django.conf import settings
from django.core import signing
from django.core.cache import cache

from accounts.constants import error_codes, messages
from accounts.constants.cache import VERIFY_RESEND_KEY
from accounts.services import email_service, hooks
from accounts.services.tokens import make_verification_token, read_verification_token
from common.email.utils import normalize_email
from common.exception.domain import InvalidTokenException, TokenExpiredException


def verify_email(token: str) -> EmailAddress:
    """Single use: once the address is verified the same link is rejected."""
    try:
        address_id = read_verification_token(token)
    except signing.SignatureExpired as exc:
        raise TokenExpiredException(
            messages.VERIFICATION_LINK_EXPIRED,
            error_code=error_codes.VERIFICATION_TOKEN_EXPIRED,
        ) from exc
    except signing.BadSignature as exc:
        raise InvalidTokenException(
            messages.VERIFICATION_LINK_INVALID,
            error_code=error_codes.VERIFICATION_TOKEN_INVALID,
        ) from exc

    address = EmailAddress.objects.filter(pk=address_id).select_related("user").first()
    if address is None or address.verified:
        raise InvalidTokenException(
            messages.VERIFICATION_LINK_INVALID,
            error_code=error_codes.VERIFICATION_TOKEN_INVALID,
        )

    address.set_verified(commit=True)
    hooks.run_user_activated(address.user)
    return address


def resend_verification(email: str) -> None:
    """Neutral by design: the cooldown is taken before looking the email up, so
    the reply never depends on whether the account exists."""
    email = normalize_email(email)
    cooldown_key = VERIFY_RESEND_KEY.format(email=email)
    if not cache.add(cooldown_key, 1, settings.EMAIL_VERIFICATION_RESEND_COOLDOWN):
        return

    address = (
        EmailAddress.objects.filter(
            email__iexact=email, verified=False, user__is_active=True
        )
        .order_by("-primary")
        .first()
    )
    if address is not None:
        email_service.send_verification_email(
            address.email, make_verification_token(address.pk)
        )
