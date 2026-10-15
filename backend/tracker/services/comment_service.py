from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from common.exception.domain import PermissionDeniedException
from projects import permissions
from projects.constants import error_codes as project_error_codes
from projects.constants import permissions as codes
from projects.models import Membership
from projects.services import access as project_access
from projects.services import activity
from tracker.constants import actions, error_codes, messages
from tracker.models import Comment, Task
from tracker.services import access, mention_service


def list_comments(task: Task) -> QuerySet[Comment]:
    # Deleted comments stay in the list as placeholders without their body.
    return Comment.all_objects.filter(task=task).select_related("author")


def _task_path(task: Task) -> str:
    return f"tasks/{task.number}"


def _require_author_or_moderator(membership: Membership, comment: Comment) -> None:
    if comment.author_id == membership.user_id:
        return
    if not permissions.has_permission(membership, codes.COMMENT_MODERATE):
        raise PermissionDeniedException(
            messages.COMMENT_NOT_YOURS,
            error_code=project_error_codes.PERMISSION_DENIED,
        )


@transaction.atomic
def create(
    membership: Membership, task: Task, body: str, ip: str | None = None
) -> Comment:
    permissions.require_permission(membership, codes.COMMENT_CREATE)
    project_access.ensure_writable(membership.project)
    comment = Comment.objects.create(task=task, author=membership.user, body=body)
    mention_service.notify_new_mentions(
        membership.project,
        membership.user,
        old_body="",
        new_body=body,
        where=f"a comment on {task.key}",
        path=_task_path(task),
    )
    activity.log(
        membership.project,
        membership.user,
        actions.COMMENT_CREATED,
        actions.ENTITY_COMMENT,
        comment.pk,
        {"task": task.number},
        ip,
    )
    return comment


def _editable(membership: Membership, task: Task, comment_id: UUID) -> Comment:
    comment = access.get_comment(task, comment_id)
    if comment.is_deleted:
        raise access.conflict(
            messages.COMMENT_ALREADY_DELETED, error_codes.COMMENT_DELETED
        )
    _require_author_or_moderator(membership, comment)
    return comment


@transaction.atomic
def edit(
    membership: Membership,
    task: Task,
    comment_id: UUID,
    body: str,
    ip: str | None = None,
) -> Comment:
    project_access.ensure_writable(membership.project)
    comment = _editable(membership, task, comment_id)
    old_body = comment.body
    if body != old_body:
        comment.body = body
        comment.edited_at = timezone.now()
        comment.save(update_fields=["body", "edited_at", "updated_at"])
        mention_service.notify_new_mentions(
            membership.project,
            membership.user,
            old_body=old_body,
            new_body=body,
            where=f"a comment on {task.key}",
            path=_task_path(task),
        )
        activity.log(
            membership.project,
            membership.user,
            actions.COMMENT_EDITED,
            actions.ENTITY_COMMENT,
            comment.pk,
            {"task": task.number},
            ip,
        )
    return comment


@transaction.atomic
def delete(
    membership: Membership, task: Task, comment_id: UUID, ip: str | None = None
) -> Comment:
    project_access.ensure_writable(membership.project)
    comment = _editable(membership, task, comment_id)
    comment.is_deleted = True
    comment.deleted_at = timezone.now()
    comment.deleted_by = membership.user
    comment.save(update_fields=["is_deleted", "deleted_at", "deleted_by", "updated_at"])
    activity.log(
        membership.project,
        membership.user,
        actions.COMMENT_DELETED,
        actions.ENTITY_COMMENT,
        comment.pk,
        {"task": task.number},
        ip,
    )
    return comment
