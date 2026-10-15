import re
from uuid import UUID

from django.conf import settings

from accounts.models import User
from accounts.services.email_service import queue_email
from projects.models import Membership, Project
from tracker.constants import emails

MENTION_PATTERN = re.compile(
    r"@\[user:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\]"
)


def extract(body: str) -> set[UUID]:
    return {UUID(match) for match in MENTION_PATTERN.findall(body or "")}


def notify_new_mentions(
    project: Project,
    author: User,
    *,
    old_body: str,
    new_body: str,
    where: str,
    path: str,
) -> list[User]:
    """Email each member mentioned in `new_body` but not in `old_body`. Only
    current project members count and nobody is notified about themselves."""
    wanted = extract(new_body) - extract(old_body) - {author.pk}
    if not wanted:
        return []
    members = [
        m.user
        for m in Membership.objects.filter(
            project=project, user_id__in=wanted
        ).select_related("user")
    ]
    for user in members:
        queue_email(
            emails.MENTION_SUBJECT.format(
                author=author.display_name, project=project.name
            ),
            emails.MENTION_BODY.format(
                author=author.display_name,
                where=where,
                project=project.name,
                project_id=project.pk,
                path=path,
                frontend_url=settings.FRONTEND_URL,
            ),
            user.email,
        )
    return members
