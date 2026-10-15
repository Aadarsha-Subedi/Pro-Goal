from django.conf import settings

from accounts.models import User
from accounts.services.email_service import queue_email
from projects.constants import emails
from projects.models import Project


def _frontend() -> dict:
    return {"frontend_url": settings.FRONTEND_URL}


def send_join_request_email(project: Project, requester: User) -> None:
    if project.owner.is_system:
        return
    queue_email(
        emails.JOIN_REQUEST_SUBJECT.format(project=project.name),
        emails.JOIN_REQUEST_BODY.format(
            requester=requester.display_name,
            email=requester.email,
            project=project.name,
            project_id=project.pk,
            **_frontend(),
        ),
        project.owner.email,
    )


def send_join_decision_email(project: Project, requester: User, approved: bool) -> None:
    if approved:
        subject = emails.JOIN_APPROVED_SUBJECT
        body = emails.JOIN_APPROVED_BODY
    else:
        subject = emails.JOIN_REJECTED_SUBJECT
        body = emails.JOIN_REJECTED_BODY
    queue_email(
        subject.format(project=project.name),
        body.format(project=project.name, project_id=project.pk, **_frontend()),
        requester.email,
    )


def send_member_removed_email(project: Project, removed: User) -> None:
    queue_email(
        emails.MEMBER_REMOVED_SUBJECT.format(project=project.name),
        emails.MEMBER_REMOVED_BODY.format(project=project.name),
        removed.email,
    )


def send_transfer_offer_email(project: Project, owner: User, to_user: User) -> None:
    queue_email(
        emails.TRANSFER_OFFER_SUBJECT.format(project=project.name),
        emails.TRANSFER_OFFER_BODY.format(
            owner=owner.display_name,
            project=project.name,
            project_id=project.pk,
            **_frontend(),
        ),
        to_user.email,
    )


def send_transfer_accepted_email(
    project: Project, old_owner: User, new_owner: User
) -> None:
    queue_email(
        emails.TRANSFER_ACCEPTED_SUBJECT.format(project=project.name),
        emails.TRANSFER_ACCEPTED_BODY.format(
            new_owner=new_owner.display_name, project=project.name
        ),
        old_owner.email,
    )
