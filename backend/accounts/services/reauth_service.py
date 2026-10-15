from dataclasses import dataclass

from allauth.socialaccount.models import SocialAccount

from accounts.constants import error_codes, messages
from accounts.constants.auth import GOOGLE_PROVIDER
from accounts.models import User
from accounts.services.google_service import (
    GoogleIdTokenVerifier,
    GoogleTokenVerifier,
)
from common.exception.domain import (
    AppException,
    PermissionDeniedException,
    ValidationException,
)


@dataclass(frozen=True)
class Reauth:
    """Proof of identity sent with a sensitive request."""

    password: str | None = None
    id_token: str | None = None


def confirm(
    user: User, reauth: Reauth, verifier: GoogleTokenVerifier | None = None
) -> None:
    """Re-authenticate before a sensitive action: the account password, or for
    social-only users a fresh Google ID token that belongs to the same account."""
    if reauth.password:
        if user.has_usable_password() and user.check_password(reauth.password):
            return
        raise _failed()
    if reauth.id_token:
        try:
            profile = (verifier or GoogleIdTokenVerifier()).verify(reauth.id_token)
        except AppException:
            raise _failed() from None
        linked = SocialAccount.objects.filter(
            user=user, provider=GOOGLE_PROVIDER, uid=profile.sub
        ).exists()
        if linked and profile.email_verified:
            return
        raise _failed()
    raise ValidationException(
        messages.REAUTH_REQUIRED, error_code=error_codes.REAUTH_REQUIRED
    )


def _failed() -> AppException:
    return PermissionDeniedException(
        messages.REAUTH_FAILED, error_code=error_codes.REAUTH_FAILED
    )
