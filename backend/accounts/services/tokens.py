from django.conf import settings
from django.core import signing

from accounts.constants.auth import EMAIL_CHANGE_SALT, VERIFY_SALT


def make_verification_token(email_address_id: int) -> str:
    return signing.dumps({"email_address_id": email_address_id}, salt=VERIFY_SALT)


def read_verification_token(token: str) -> int:
    """Return the EmailAddress id. Raises signing.SignatureExpired / BadSignature."""
    payload = signing.loads(
        token, salt=VERIFY_SALT, max_age=settings.EMAIL_VERIFICATION_TIMEOUT
    )
    return int(payload["email_address_id"])


def make_email_change_token(pending_id: str) -> str:
    return signing.dumps({"pending": str(pending_id)}, salt=EMAIL_CHANGE_SALT)


def read_email_change_token(token: str) -> str:
    """Return the PendingEmailChange id. Raises signing.SignatureExpired / BadSignature."""
    payload = signing.loads(
        token, salt=EMAIL_CHANGE_SALT, max_age=settings.EMAIL_VERIFICATION_TIMEOUT
    )
    return str(payload["pending"])
