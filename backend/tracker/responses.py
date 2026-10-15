from dataclasses import dataclass

from accounts.models import User
from common.response.domain import BaseResponseData
from projects.responses import public_user
from tracker.constants.categories import StatusCategory
from tracker.models import (
    Comment,
    KanbanPreference,
    Note,
    NoteRevision,
    Priority,
    Status,
    Task,
)
from tracker.services import query, task_service

DELETED_USER = {"id": None, "first_name": "Deleted user", "avatar_url": None}


def user_or_deleted(user: User | None) -> dict:
    """Authors and creators outlive their accounts: show "Deleted user"."""
    return public_user(user) if user is not None else dict(DELETED_USER)


def _iso(value) -> str | None:
    return value.isoformat() if value else None


@dataclass(frozen=True)
class StatusData(BaseResponseData):
    status: Status

    def to_dict(self) -> dict:
        status = self.status
        return {
            "id": str(status.pk),
            "name": status.name,
            "category": status.category,
            "position": status.position,
            "is_default": status.is_default,
        }


@dataclass(frozen=True)
class PriorityData(BaseResponseData):
    priority: Priority

    def to_dict(self) -> dict:
        priority = self.priority
        return {
            "id": str(priority.pk),
            "name": priority.name,
            "rank": priority.rank,
            "position": priority.position,
            "is_default": priority.is_default,
        }


@dataclass(frozen=True)
class TaskData(BaseResponseData):
    """A task. `detail=False` (lists) leaves out the long description."""

    task: Task
    detail: bool = True

    def to_dict(self) -> dict:
        task = self.task
        assignees = [ta.user for ta in task.task_assignees.all()]
        subtasks = list(
            getattr(task, "live_subtasks", None)
            or task.subtasks.select_related("status")
        )
        is_done = task.status.category == StatusCategory.DONE
        data = {
            "id": str(task.pk),
            "number": task.number,
            "key": task.key,
            "project": {
                "id": str(task.project_id),
                "name": task.project.name,
                "task_key": task.project.task_key,
            },
            "title": task.title,
            "status": {
                "id": str(task.status_id),
                "name": task.status.name,
                "category": task.status.category,
            },
            "priority": {
                "id": str(task.priority_id),
                "name": task.priority.name,
                "rank": task.priority.rank,
            },
            "start_date": _iso(task.start_date),
            "due_date": _iso(task.due_date),
            "is_overdue": bool(
                task.due_date and task.due_date < query.today() and not is_done
            ),
            "parent_number": task.parent.number if task.parent_id else None,
            "subtasks": {
                "total": len(subtasks),
                "done": sum(
                    1 for s in subtasks if s.status.category == StatusCategory.DONE
                ),
            },
            "assignees": [public_user(u) for u in assignees],
            "tags": sorted(tt.tag.name for tt in task.task_tags.all()),
            "created_by": user_or_deleted(task.created_by),
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "deleted_at": _iso(task.deleted_at),
            "deletion_scheduled_for": _iso(task_service.deletion_scheduled_for(task)),
        }
        if self.detail:
            data["description"] = task.description
        return data


@dataclass(frozen=True)
class NoteData(BaseResponseData):
    note: Note
    detail: bool = True

    def to_dict(self) -> dict:
        note = self.note
        data = {
            "id": str(note.pk),
            "title": note.title,
            "version": note.version,
            "tags": sorted(nt.tag.name for nt in note.note_tags.all()),
            "author": user_or_deleted(note.author),
            "created_at": note.created_at.isoformat(),
            "updated_at": note.updated_at.isoformat(),
        }
        if self.detail:
            data["body"] = note.body
        return data


@dataclass(frozen=True)
class NoteRevisionData(BaseResponseData):
    revision: NoteRevision

    def to_dict(self) -> dict:
        revision = self.revision
        return {
            "id": str(revision.pk),
            "version": revision.version,
            "title": revision.title,
            "body": revision.body,
            "edited_by": user_or_deleted(revision.edited_by),
            "created_at": revision.created_at.isoformat(),
        }


@dataclass(frozen=True)
class CommentData(BaseResponseData):
    comment: Comment

    def to_dict(self) -> dict:
        comment = self.comment
        return {
            "id": str(comment.pk),
            "author": user_or_deleted(comment.author),
            "body": None if comment.is_deleted else comment.body,
            "is_deleted": comment.is_deleted,
            "edited_at": _iso(comment.edited_at),
            "deleted_at": _iso(comment.deleted_at),
            "created_at": comment.created_at.isoformat(),
        }


@dataclass(frozen=True)
class PreferenceData(BaseResponseData):
    preference: KanbanPreference

    def to_dict(self) -> dict:
        return {
            "group_by": self.preference.group_by,
            "sort_by": self.preference.sort_by,
        }
