from uuid import UUID

from django.db.models import Model

from common.exception.domain import ConflictException, NotFoundException
from projects.models import Membership, Project
from tracker.constants import error_codes, messages
from tracker.models import Comment, Note, Priority, Status, Task


def _not_found(message: str, code: str) -> NotFoundException:
    return NotFoundException(message, error_code=code)


def get_task(
    membership: Membership, number: int, *, allow_deleted: bool = False
) -> Task:
    task = (
        Task.all_objects.select_related("project", "status", "priority", "created_by")
        .filter(project=membership.project, number=number)
        .first()
    )
    if task is None or (task.is_deleted and not allow_deleted):
        raise _not_found(messages.TASK_NOT_FOUND, error_codes.TASK_NOT_FOUND)
    return task


def get_note(membership: Membership, note_id: UUID) -> Note:
    note = (
        Note.objects.select_related("project", "author")
        .filter(project=membership.project, pk=note_id)
        .first()
    )
    if note is None:
        raise _not_found(messages.NOTE_NOT_FOUND, error_codes.NOTE_NOT_FOUND)
    return note


def get_comment(task: Task, comment_id: UUID) -> Comment:
    comment = (
        Comment.all_objects.select_related("author")
        .filter(task=task, pk=comment_id)
        .first()
    )
    if comment is None:
        raise _not_found(messages.COMMENT_NOT_FOUND, error_codes.COMMENT_NOT_FOUND)
    return comment


def get_status(project: Project, status_id: UUID) -> Status:
    status = Status.objects.filter(project=project, pk=status_id).first()
    if status is None:
        raise _not_found(messages.STATUS_NOT_FOUND, error_codes.STATUS_NOT_FOUND)
    return status


def get_priority(project: Project, priority_id: UUID) -> Priority:
    priority = Priority.objects.filter(project=project, pk=priority_id).first()
    if priority is None:
        raise _not_found(messages.PRIORITY_NOT_FOUND, error_codes.PRIORITY_NOT_FOUND)
    return priority


def conflict(message: str, code: str) -> ConflictException:
    return ConflictException(message, error_code=code)


def same_project(obj: Model, project: Project) -> bool:
    return obj.project_id == project.pk
