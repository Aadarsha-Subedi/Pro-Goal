from django.utils import timezone

from projects.views.base import ip_of, paginated

__all__ = ["ip_of", "paginated", "server_meta"]


def server_meta() -> dict:
    """Server time travels with task lists so the UI never judges "overdue" or
    countdowns from the browser clock."""
    now = timezone.now()
    return {"server_time": now.isoformat(), "server_date": now.date().isoformat()}
