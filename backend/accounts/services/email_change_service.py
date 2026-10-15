from datetime import timedelta

from allauth.account.models import EmailAddress
from django.core import signing
from django.db import IntegrityError, transaction
from django.http import HttpRequest
from django.utils import timezone

from accounts.constants import error_codes, fields, messages
from accounts.models import PendingEmailChange, User
from accounts.services import email_service, reauth_service, session_service
from accounts.services.reauth_service import Reauth
from accounts.services.tokens import make_email_change_token, read_email_change_token
from common.email.utils import mask_email, normalize_email
from common.exception.domain import (
    InvalidTokenException,
    TokenExpiredException,
    ValidationException,
)
from common.validators.disposable import ensure_not_disposable
from security.constants.events import EventType
from security.services import event_service


def _address_is_taken(email: str) -> bool:
    return (
        User.objects.filter(email__iexact=email).exists()
        or EmailAddress.objects.filter(email__iexact=email, verified=True).exists()
    )


@transaction.atomic
def request_change(user: User, new_email: str, reauth: Reauth, verifier=None) -> None:
    """Ask to change the login address. Needs a fresh password or Google
    confirmation. The reply never reveals whether the new address is taken: the
    link goes only to the new address, and the old one is warned right away."""
    reauth_service.confirm(user, reauth, verifier)
    new_email = normalize_email(new_email)
    ensure_not_disposable(
        new_email,
        field="new_email",
        message=messages.DISPOSABLE_EMAIL,
        error_code=error_codes.DISPOSABLE_EMAIL,
    )
    if new_email == normalize_email(user.email):
        raise ValidationException(
            errors=[{"field": "new_email", "message": messages.SAME_EMAIL}],
            error_code=error_codes.SAME_EMAIL,
        )
    if _address_is_taken(new_email):
        return
    try:
        with transaction.atomic():
            PendingEmailChange.objects.filter(user=user).delete()
            pending = PendingEmailChange.objects.create(user=user, new_email=new_email)
    except IntegrityError:
        return
    email_service.send_email_change_link(new_email, make_email_change_token(pending.pk))
    email_service.send_email_change_requested_alert(user.email, mask_email(new_email))


def _invalid() -> InvalidTokenException:
    return InvalidTokenException(
        messages.EMAIL_CHANGE_LINK_INVALID,
        error_code=error_codes.EMAIL_CHANGE_TOKEN_INVALID,
    )


@transaction.atomic
def confirm_change(request: HttpRequest, token: str) -> User:
    """Complete the change from the emailed link. The link proves control of the
    new address, so no login is needed (it may open in another browser)."""
    try:
        pending_id = read_email_change_token(token)
    except signing.SignatureExpired as exc:
        raise TokenExpiredException(
            messages.EMAIL_CHANGE_LINK_INVALID,
            error_code=error_codes.EMAIL_CHANGE_TOKEN_EXPIRED,
        ) from exc
    except signing.BadSignature as exc:
        raise _invalid() from exc

    pending = (
        PendingEmailChange.objects.select_for_update(of=("self",))
        .select_related("user")
        .filter(pk=pending_id)
        .first()
    )
    if pending is None or _address_is_taken(pending.new_email):
        raise _invalid()

    user, old_email, new_email = pending.user, pending.user.email, pending.new_email
    user.email = new_email
    user.save(update_fields=["email", "updated_at"])
    # The new address becomes the only login address.
    EmailAddress.objects.filter(user=user).delete()
    EmailAddress.objects.create(user=user, email=new_email, primary=True, verified=True)
    pending.delete()
    # Signed in sessions belong to the old identity: everyone signs in again.
    session_service.revoke_all(user)
    if hasattr(request, "session"):
        request.session.flush()
    event_service.record(request, user, EventType.EMAIL_CHANGED)
    email_service.send_email_changed_alert(old_email, mask_email(new_email))
    return user


def purge_stale_requests() -> int:
    """Unconfirmed requests older than a day are dropped."""
    cutoff = timezone.now() - timedelta(hours=fields.EMAIL_CHANGE_RETENTION_HOURS)
    deleted, _ = PendingEmailChange.objects.filter(created_at__lt=cutoff).delete()
    return deleted
