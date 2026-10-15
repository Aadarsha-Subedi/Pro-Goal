from allauth.account.models import EmailAddress
from django.db import IntegrityError, transaction

from accounts.constants import error_codes, messages
from accounts.models import User
from accounts.services import email_service
from accounts.services.tokens import make_verification_token
from common.email.utils import normalize_email
from common.validators.disposable import ensure_not_disposable
from common.validators.password import validate_password_strength


def sign_up(
    *, email: str, password: str, first_name: str, last_name: str, display_name: str
) -> None:
    """Create an unverified account. The caller always gets the same neutral
    reply: when the email is taken we mail the owner instead of failing."""
    email = normalize_email(email)
    ensure_not_disposable(
        email,
        field="email",
        message=messages.DISPOSABLE_EMAIL,
        error_code=error_codes.DISPOSABLE_EMAIL,
    )
    candidate = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        display_name=display_name,
    )
    validate_password_strength(password, candidate)

    if User.objects.filter(email__iexact=email).exists():
        email_service.send_already_registered_email(email)
        return

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                display_name=display_name,
            )
            address = EmailAddress.objects.create(
                user=user, email=email, primary=True, verified=False
            )
            email_service.send_verification_email(
                email, make_verification_token(address.pk)
            )
    except IntegrityError:
        # Lost a race with a concurrent signup for the same email.
        email_service.send_already_registered_email(email)
