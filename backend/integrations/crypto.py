from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings

from common.exception.domain import ServiceUnavailableException
from integrations.constants import error_codes, messages


def _fernet() -> MultiFernet:
    """The first configured key encrypts; every key can decrypt, so a new key
    is rotated in by putting it first."""
    keys = settings.INTEGRATION_ENCRYPTION_KEYS
    if not keys:
        raise ServiceUnavailableException(
            messages.NOT_CONFIGURED, error_code=error_codes.NOT_CONFIGURED
        )
    try:
        return MultiFernet([Fernet(key.encode()) for key in keys])
    except ValueError:
        # Say what is wrong without echoing the key.
        raise ServiceUnavailableException(
            messages.INVALID_KEY, error_code=error_codes.INVALID_KEY
        ) from None


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()


def rotate(token: str) -> str:
    """Re-encrypt `token` with the first key."""
    return _fernet().rotate(token.encode()).decode()


__all__ = ["InvalidToken", "decrypt", "encrypt", "rotate"]
