from django.db.models import QuerySet

from accounts.models import User
from security.models import SecurityEvent


def events_for(user: User, event_type: str | None = None) -> QuerySet[SecurityEvent]:
    """Only ever the caller's own events, newest first."""
    queryset = SecurityEvent.objects.filter(user=user)
    if event_type:
        queryset = queryset.filter(event_type=event_type)
    return queryset
