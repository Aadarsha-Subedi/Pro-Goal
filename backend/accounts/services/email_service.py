from django.conf import settings
from django.db import transaction

from accounts.constants import emails
from accounts.tasks import send_email


def queue_email(
    subject: str, body: str, to: str, action_label: str | None = None
) -> None:
    """Queue the email only after the surrounding transaction commits. The first
    link in `body` becomes a button; `action_label` overrides its text."""
    transaction.on_commit(lambda: send_email.delay(subject, body, to, action_label))


def send_verification_email(to: str, token: str) -> None:
    link = settings.FRONTEND_URL + emails.VERIFICATION_PATH.format(token=token)
    queue_email(
        emails.VERIFICATION_SUBJECT, emails.VERIFICATION_BODY.format(link=link), to
    )


def send_already_registered_email(to: str) -> None:
    queue_email(
        emails.ALREADY_REGISTERED_SUBJECT,
        emails.ALREADY_REGISTERED_BODY.format(frontend_url=settings.FRONTEND_URL),
        to,
    )


def send_password_reset_email(to: str, uid: str, token: str) -> None:
    link = settings.FRONTEND_URL + emails.PASSWORD_RESET_PATH.format(
        uid=uid, token=token
    )
    queue_email(
        emails.PASSWORD_RESET_SUBJECT,
        emails.PASSWORD_RESET_BODY.format(link=link),
        to,
    )


def send_password_changed_email(to: str) -> None:
    queue_email(
        emails.PASSWORD_CHANGED_SUBJECT,
        emails.PASSWORD_CHANGED_BODY.format(frontend_url=settings.FRONTEND_URL),
        to,
    )


def send_email_change_link(to: str, token: str) -> None:
    link = settings.FRONTEND_URL + emails.EMAIL_CHANGE_PATH.format(token=token)
    queue_email(
        emails.EMAIL_CHANGE_SUBJECT, emails.EMAIL_CHANGE_BODY.format(link=link), to
    )


def send_email_change_requested_alert(to: str, new_email: str) -> None:
    queue_email(
        emails.EMAIL_CHANGE_REQUESTED_SUBJECT,
        emails.EMAIL_CHANGE_REQUESTED_BODY.format(
            new_email=new_email, frontend_url=settings.FRONTEND_URL
        ),
        to,
    )


def send_email_changed_alert(to: str, new_email: str) -> None:
    queue_email(
        emails.EMAIL_CHANGED_SUBJECT,
        emails.EMAIL_CHANGED_BODY.format(new_email=new_email),
        to,
    )
