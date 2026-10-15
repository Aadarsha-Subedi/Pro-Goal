import hashlib

from django.core.cache import cache

from common.email.utils import normalize_email
from common.exception.domain import ThrottledException
from security.constants import error_codes, messages
from security.constants.cache import LOGIN_FAILURES_KEY, LOGIN_LOCK_ALERTED_KEY
from security.constants.limits import LOGIN_FAILURE_WINDOW_SECONDS, MAX_LOGIN_FAILURES


def _digest(email: str) -> str:
    """Cache keys use a hash so the address itself is never stored."""
    return hashlib.sha256(normalize_email(email).encode()).hexdigest()


def failures(email: str) -> int:
    return cache.get(LOGIN_FAILURES_KEY.format(digest=_digest(email))) or 0


def is_locked(email: str) -> bool:
    return failures(email) >= MAX_LOGIN_FAILURES


def retry_after(email: str) -> int:
    """Seconds until the window ends (cache backends do not all report the
    remaining time, so fall back to the full window)."""
    key = LOGIN_FAILURES_KEY.format(digest=_digest(email))
    ttl = getattr(cache, "ttl", None)
    remaining = ttl(key) if callable(ttl) else None
    return (
        int(remaining) if remaining and remaining > 0 else LOGIN_FAILURE_WINDOW_SECONDS
    )


def check(email: str) -> None:
    """Refuse the attempt, whatever the password, while the account is locked.
    Unknown emails are counted the same way, so lockout reveals nothing."""
    if is_locked(email):
        raise ThrottledException(
            messages.LOGIN_LOCKED,
            error_code=error_codes.LOGIN_LOCKED,
            headers={"Retry-After": str(retry_after(email))},
        )


def register_failure(email: str) -> int:
    """Count a wrong password; returns the new count. Fixed window from the
    first failure."""
    key = LOGIN_FAILURES_KEY.format(digest=_digest(email))
    cache.add(key, 0, LOGIN_FAILURE_WINDOW_SECONDS)
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, LOGIN_FAILURE_WINDOW_SECONDS)
        return 1


def reset(email: str) -> None:
    digest = _digest(email)
    cache.delete_many(
        [
            LOGIN_FAILURES_KEY.format(digest=digest),
            LOGIN_LOCK_ALERTED_KEY.format(digest=digest),
        ]
    )


def first_lock_alert(email: str) -> bool:
    """True once per lockout window, so the owner gets one email, not five."""
    key = LOGIN_LOCK_ALERTED_KEY.format(digest=_digest(email))
    return bool(cache.add(key, 1, LOGIN_FAILURE_WINDOW_SECONDS))
