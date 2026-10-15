import logging

from django.http import HttpRequest

from accounts.constants.sessions import USER_AGENT_MAX_LENGTH
from accounts.models import User
from accounts.services import session_service
from security.constants.events import EventType
from security.models import SecurityEvent

logger = logging.getLogger(__name__)


def record(
    request: HttpRequest | None, user: User, event_type: EventType, **metadata: object
) -> SecurityEvent | None:
    """Append a security event for `user`. Recording must never break the
    action it describes, so failures are logged and swallowed."""
    try:
        user_agent = ""
        ip = None
        if request is not None:
            user_agent = request.META.get("HTTP_USER_AGENT", "")[:USER_AGENT_MAX_LENGTH]
            ip = session_service.client_ip(request)
        return SecurityEvent.objects.create(
            user=user,
            event_type=event_type,
            ip=ip,
            user_agent=user_agent,
            device_name=session_service.device_name(user_agent) if user_agent else "",
            metadata=metadata,
        )
    except Exception:
        logger.exception("Could not record security event %s", event_type)
        return None
