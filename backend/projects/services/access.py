from uuid import UUID

from django.db.models import QuerySet

from accounts.models import User
from common.exception.domain import ConflictException, NotFoundException
from projects.constants import error_codes, messages
from projects.models import Membership, Project


def memberships_for(user: User) -> QuerySet[Membership]:
    return Membership.objects.filter(user=user).select_related("project", "user")


def get_membership(
    user: User, project_id: UUID, *, allow_deleted: bool = False
) -> Membership:
    """The caller's membership, or 404 so project ids cannot be probed. Only the
    owner can reach a project scheduled for deletion (to restore it)."""
    membership = (
        memberships_for(user)
        .filter(project_id=project_id)
        .select_related("project__owner")
        .first()
    )
    if membership is None:
        raise NotFoundException(
            messages.PROJECT_NOT_FOUND, error_code=error_codes.PROJECT_NOT_FOUND
        )
    project = membership.project
    if project.is_deleted:
        if not membership.is_owner:
            raise NotFoundException(
                messages.PROJECT_NOT_FOUND, error_code=error_codes.PROJECT_NOT_FOUND
            )
        if not allow_deleted:
            raise ConflictException(
                messages.PROJECT_IS_DELETED, error_code=error_codes.PROJECT_DELETED
            )
    return membership


def ensure_not_demo(project: Project) -> None:
    """Demo projects are shared, so their settings never change."""
    if project.is_demo:
        raise ConflictException(
            messages.DEMO_PROJECT_LOCKED, error_code=error_codes.DEMO_PROJECT_LOCKED
        )


def ensure_writable(project: Project) -> None:
    if project.is_archived:
        raise ConflictException(
            messages.PROJECT_IS_ARCHIVED, error_code=error_codes.PROJECT_ARCHIVED
        )
