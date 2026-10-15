from django.utils import timezone

from accounts.models import User


def update_profile(user: User, **fields: str) -> User:
    for name, value in fields.items():
        setattr(user, name, value.strip())
    user.save(update_fields=[*fields, "updated_at"])
    return user


def set_tour_completed(user: User, completed: bool) -> User:
    user.tour_completed_at = timezone.now() if completed else None
    user.save(update_fields=["tour_completed_at", "updated_at"])
    return user
