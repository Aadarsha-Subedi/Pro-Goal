from importlib import import_module

from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone
from rest_framework.throttling import BaseThrottle

from accounts.constants import error_codes, messages
from accounts.constants import sessions as session_constants
from accounts.models import User, UserSession
from common.exception.domain import NotFoundException


def _session_store(session_key: str):
    engine = import_module(settings.SESSION_ENGINE)
    return engine.SessionStore(session_key=session_key)


def _first_label(ua: str, tokens: tuple[tuple[str, str], ...], default: str) -> str:
    return next((label for token, label in tokens if token in ua), default)


def device_name(user_agent: str) -> str:
    ua = user_agent.lower()
    os_name = _first_label(
        ua, session_constants.OS_TOKENS, session_constants.UNKNOWN_OS
    )
    browser = _first_label(
        ua, session_constants.BROWSER_TOKENS, session_constants.UNKNOWN_BROWSER
    )
    return f"{browser} on {os_name}"


def client_ip(request: HttpRequest) -> str | None:
    ip = BaseThrottle().get_ident(request)
    return None if ip in (None, "") else ip


def register_session(
    request: HttpRequest, user: User, remember_me: bool
) -> UserSession:
    """Record the request's (already saved) Django session as a UserSession."""
    request.session.save()
    user_agent = request.META.get("HTTP_USER_AGENT", "")[
        : session_constants.USER_AGENT_MAX_LENGTH
    ]
    return UserSession.objects.update_or_create(
        session_key=request.session.session_key,
        defaults={
            "user": user,
            "device_name": device_name(user_agent),
            "ip": client_ip(request),
            "user_agent": user_agent,
            "last_seen_at": timezone.now(),
            "remember_me": remember_me,
        },
    )[0]


def destroy_session(session_key: str) -> None:
    _session_store(session_key).delete()
    UserSession.objects.filter(session_key=session_key).delete()


def revoke_all(user: User, *, except_key: str | None = None) -> None:
    sessions = UserSession.objects.filter(user=user)
    if except_key:
        sessions = sessions.exclude(session_key=except_key)
    for session_key in list(sessions.values_list("session_key", flat=True)):
        destroy_session(session_key)


def list_sessions(user: User) -> list[UserSession]:
    return list(UserSession.objects.filter(user=user))


def revoke(user: User, session_id: str) -> str:
    """Revoke one of the user's sessions. Returns its session key."""
    session = UserSession.objects.filter(user=user, pk=session_id).first()
    if session is None:
        raise NotFoundException(
            messages.SESSION_NOT_FOUND, error_code=error_codes.SESSION_NOT_FOUND
        )
    key = session.session_key
    destroy_session(key)
    return key
