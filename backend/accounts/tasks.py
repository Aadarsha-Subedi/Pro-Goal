import logging
from datetime import timedelta

import requests
from celery import shared_task
from django.contrib.sessions.models import Session
from django.utils import timezone

from accounts.constants.avatar import GOOGLE_AVATAR_TIMEOUT_SECONDS
from accounts.constants.sessions import STALE_SESSION_GRACE_MINUTES
from accounts.constants.tasks import DEFAULT_QUEUE
from accounts.models import User, UserSession
from common.email.render import build_message

logger = logging.getLogger(__name__)


@shared_task(queue=DEFAULT_QUEUE)
def send_email(
    subject: str, body: str, to: str, action_label: str | None = None
) -> None:
    build_message(subject, body, to, action_label).send()


@shared_task(queue=DEFAULT_QUEUE)
def import_google_avatar(user_id: str, picture_url: str) -> None:
    from accounts.services.avatar_service import AvatarError, set_avatar

    user = User.objects.filter(pk=user_id).first()
    if user is None or user.avatar:
        return
    try:
        response = requests.get(picture_url, timeout=GOOGLE_AVATAR_TIMEOUT_SECONDS)
        response.raise_for_status()
        set_avatar(user, response.content)
    except requests.RequestException, AvatarError:
        logger.warning("Could not import Google avatar", extra={"user_id": user_id})


@shared_task(queue=DEFAULT_QUEUE)
def purge_deleted_accounts() -> int:
    from accounts.services.deletion_service import purge_expired_accounts

    return purge_expired_accounts()


@shared_task(queue=DEFAULT_QUEUE)
def clear_expired_sessions() -> int:
    """Drop expired Django sessions and the UserSession rows that point at
    sessions which no longer exist."""
    Session.objects.filter(expire_date__lt=timezone.now()).delete()
    live_keys = Session.objects.values("session_key")
    stale = UserSession.objects.exclude(session_key__in=live_keys)
    # Skip rows created in the last minute: their Session may not be committed yet.
    stale = stale.filter(
        created_at__lt=timezone.now() - timedelta(minutes=STALE_SESSION_GRACE_MINUTES)
    )
    deleted, _ = stale.delete()
    return deleted


@shared_task(queue=DEFAULT_QUEUE)
def purge_stale_email_changes() -> int:
    from accounts.services.email_change_service import purge_stale_requests

    return purge_stale_requests()
