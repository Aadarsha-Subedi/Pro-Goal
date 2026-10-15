from accounts.models import User
from integrations.models import NotificationPreference
from integrations.slack import constants


def list_for(user: User) -> list[dict]:
    """The personal events with the user's effective choices (defaults when
    they never changed one)."""
    saved = {p.event_type: p for p in NotificationPreference.objects.filter(user=user)}
    result = []
    for event in constants.PERSONAL_EVENTS:
        row = saved.get(event.value)
        result.append(
            {
                "event_type": event.value,
                "slack_dm": row.slack_dm if row else True,
                "email": row.email if row else False,
            }
        )
    return result


def update(user: User, changes: dict[str, dict]) -> list[dict]:
    """Apply per-event changes; fields left out keep their current value."""
    for event_type, values in changes.items():
        row, _ = NotificationPreference.objects.get_or_create(
            user=user, event_type=event_type
        )
        for field in ("slack_dm", "email"):
            if field in values:
                setattr(row, field, values[field])
        row.save()
    return list_for(user)
