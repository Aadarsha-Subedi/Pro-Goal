import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from accounts.constants.cache import SESSION_SEEN_FIELD, SESSION_TOUCH_INTERVAL_SECONDS
from accounts.models import UserSession


class UserSessionMiddleware:
    """Keeps `UserSession.last_seen_at` fresh and slides the session expiry, at most
    once a minute per session so ordinary traffic does not become a write per request.

    The last stamp lives in the session itself, which is already loaded, so the check
    costs no extra Redis or database call. Stamping marks the session modified, and
    SessionMiddleware then saves it with a new expiry."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        key = request.session.session_key
        user = getattr(request, "user", None)
        if not (key and user is not None and user.is_authenticated):
            return response
        now = time.time()
        last = request.session.get(SESSION_SEEN_FIELD, 0)
        if now - last >= SESSION_TOUCH_INTERVAL_SECONDS:
            request.session[SESSION_SEEN_FIELD] = now
            UserSession.objects.filter(session_key=key).update(
                last_seen_at=timezone.now()
            )
        return response
