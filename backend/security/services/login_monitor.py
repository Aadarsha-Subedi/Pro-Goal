from django.conf import settings
from django.http import HttpRequest

from accounts.models import User
from accounts.services import session_service
from accounts.services.email_service import queue_email
from security.constants import emails
from security.constants.events import EventType
from security.constants.limits import MAX_LOGIN_FAILURES
from security.models import SecurityEvent
from security.services import event_service, lockout_service


def _device(request: HttpRequest) -> str:
    return session_service.device_name(request.META.get("HTTP_USER_AGENT", ""))


def on_login_success(request: HttpRequest, user: User) -> None:
    """Record the sign-in, clear the failure counter and warn about a device
    this account has not signed in from before (never on the first sign-in)."""
    device = _device(request)
    earlier = SecurityEvent.objects.filter(
        user=user, event_type=EventType.LOGIN_SUCCESS
    )
    seen_before = earlier.exists()
    known_device = earlier.filter(device_name=device).exists()
    event_service.record(request, user, EventType.LOGIN_SUCCESS)
    lockout_service.reset(user.email)
    if seen_before and not known_device:
        queue_email(
            emails.NEW_DEVICE_SUBJECT,
            emails.NEW_DEVICE_BODY.format(
                device=device, frontend_url=settings.FRONTEND_URL
            ),
            user.email,
        )


def on_login_failure(request: HttpRequest, email: str, user: User | None) -> None:
    """Count a wrong password. Known accounts also get a security event, and
    one alert email when the attempts reach the lockout limit."""
    count = lockout_service.register_failure(email)
    if user is None:
        return
    event_service.record(request, user, EventType.LOGIN_FAILURE)
    if count >= MAX_LOGIN_FAILURES:
        event_service.record(request, user, EventType.LOGIN_LOCKED)
        if lockout_service.first_lock_alert(email):
            queue_email(
                emails.LOCKED_SUBJECT,
                emails.LOCKED_BODY.format(frontend_url=settings.FRONTEND_URL),
                user.email,
            )
