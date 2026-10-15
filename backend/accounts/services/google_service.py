from abc import ABC, abstractmethod
from dataclasses import dataclass

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.conf import settings
from django.db import transaction
from django.http import HttpRequest
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from accounts.constants import error_codes, messages
from accounts.constants.auth import GOOGLE_PROVIDER
from accounts.models import User
from accounts.services import auth_service, hooks
from accounts.tasks import import_google_avatar
from common.email.utils import normalize_email
from common.exception.domain import AuthenticationDeniedException
from security.constants.events import EventType
from security.services import event_service


@dataclass(frozen=True)
class GoogleProfile:
    sub: str
    email: str
    email_verified: bool
    first_name: str
    last_name: str
    name: str
    picture: str
    raw: dict


class GoogleTokenVerifier(ABC):
    """Role: turns a Google ID token into a profile, or fails."""

    @abstractmethod
    def verify(self, token: str) -> GoogleProfile:
        """Raise AuthenticationDeniedException if the token is not valid."""


class GoogleIdTokenVerifier(GoogleTokenVerifier):
    """Concrete verifier using google-auth against our OAuth client id."""

    def verify(self, token: str) -> GoogleProfile:
        try:
            claims = google_id_token.verify_oauth2_token(
                token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID
            )
        except (ValueError, GoogleAuthError) as exc:
            raise AuthenticationDeniedException(
                messages.GOOGLE_SIGN_IN_FAILED,
                error_code=error_codes.GOOGLE_TOKEN_INVALID,
            ) from exc
        return GoogleProfile(
            sub=claims["sub"],
            email=normalize_email(claims.get("email", "")),
            email_verified=bool(claims.get("email_verified")),
            first_name=claims.get("given_name", ""),
            last_name=claims.get("family_name", ""),
            name=claims.get("name", ""),
            picture=claims.get("picture", ""),
            raw=dict(claims),
        )


def _link(user: User, profile: GoogleProfile) -> None:
    SocialAccount.objects.create(
        user=user, provider=GOOGLE_PROVIDER, uid=profile.sub, extra_data=profile.raw
    )
    # Google vouches for the address, so no verification email is needed.
    address, _ = EmailAddress.objects.get_or_create(
        user=user, email=profile.email, defaults={"primary": True, "verified": True}
    )
    if not address.verified:
        address.set_verified(commit=True)


def _find_or_create_user(profile: GoogleProfile) -> tuple[User, bool, bool]:
    """The user for a Google profile, whether Google was just linked to an
    existing account, and whether the account was just created."""
    social = (
        SocialAccount.objects.filter(provider=GOOGLE_PROVIDER, uid=profile.sub)
        .select_related("user")
        .first()
    )
    if social is not None:
        return social.user, False, False

    user = User.objects.filter(email__iexact=profile.email).first()
    if user is not None:
        # Linking by email is safe only because Google marked it verified.
        _link(user, profile)
        return user, True, False

    user = User.objects.create_user(
        email=profile.email,
        password=None,
        first_name=profile.first_name,
        last_name=profile.last_name,
        display_name=profile.name or profile.first_name,
    )
    _link(user, profile)
    if profile.picture:
        transaction.on_commit(
            lambda: import_google_avatar.delay(str(user.pk), profile.picture)
        )
    return user, False, True


def google_login(
    request: HttpRequest,
    *,
    token: str,
    remember_me: bool = False,
    nonce: str | None = None,
    verifier: GoogleTokenVerifier | None = None,
) -> User:
    profile = (verifier or GoogleIdTokenVerifier()).verify(token)
    if nonce is not None and profile.raw.get("nonce") != nonce:
        # The token was minted for a different sign-in attempt than this browser's.
        raise AuthenticationDeniedException(
            messages.GOOGLE_SIGN_IN_FAILED, error_code=error_codes.GOOGLE_TOKEN_INVALID
        )
    if not profile.email or not profile.email_verified:
        raise AuthenticationDeniedException(
            messages.GOOGLE_EMAIL_NOT_VERIFIED,
            error_code=error_codes.GOOGLE_EMAIL_NOT_VERIFIED,
        )

    with transaction.atomic():
        user, newly_linked, created = _find_or_create_user(profile)
        if not user.is_active or user.is_system:
            raise AuthenticationDeniedException(
                messages.INVALID_CREDENTIALS, error_code=error_codes.INVALID_CREDENTIALS
            )
        auth_service.start_session(request, user, remember_me)
        if newly_linked:
            event_service.record(
                request, user, EventType.SOCIAL_ACCOUNT_LINKED, provider=GOOGLE_PROVIDER
            )
        if created:
            hooks.run_user_activated(user)
    return user
