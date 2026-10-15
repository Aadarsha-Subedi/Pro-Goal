from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone


@shared_task(queue="default")
def purge_security_events() -> int:
    """Delete events older than the retention period."""
    from security.models import SecurityEvent

    cutoff = timezone.now() - timedelta(days=settings.SECURITY_EVENT_RETENTION_DAYS)
    deleted, _ = SecurityEvent.objects.filter(created_at__lt=cutoff).delete()
    return deleted
