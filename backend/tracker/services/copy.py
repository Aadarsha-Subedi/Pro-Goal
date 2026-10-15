"""Clones a project's tracker content into a new project. Run through the
`project_copied` hook while a demo project is copied to a user's workspace."""

from django.db.models import Max

from projects.models import Project
from projects.services import tag_service
from tracker.models import (
    Comment,
    Note,
    NoteRevision,
    NoteTag,
    Priority,
    Status,
    Task,
    TaskCounter,
    TaskNote,
    TaskTag,
)


def copy_content(source: Project, copy: Project) -> None:
    """Statuses, priorities, tasks (with parents and tags), notes and comments.
    Assignees, attachments and dates are not carried over. Everything the
    copy's owner would otherwise author is attributed to them."""
    owner = copy.owner
    Status.objects.filter(project=copy).delete()
    Priority.objects.filter(project=copy).delete()

    status_map: dict = {}
    for status in Status.objects.filter(project=source):
        status_map[status.pk] = Status.objects.create(
            project=copy,
            name=status.name,
            category=status.category,
            position=status.position,
            is_default=status.is_default,
        )
    priority_map: dict = {}
    for priority in Priority.objects.filter(project=source):
        priority_map[priority.pk] = Priority.objects.create(
            project=copy,
            name=priority.name,
            rank=priority.rank,
            position=priority.position,
            is_default=priority.is_default,
        )

    task_map: dict = {}
    sources = list(Task.objects.filter(project=source).order_by("number"))
    for task in sources:
        task_map[task.pk] = Task.objects.create(
            project=copy,
            number=task.number,
            title=task.title,
            description=task.description,
            status=status_map[task.status_id],
            priority=priority_map[task.priority_id],
            created_by=owner,
        )
        tag_service.sync(
            TaskTag, "task", task_map[task.pk], tag_service.names(TaskTag, "task", task)
        )
    for task in sources:
        if task.parent_id in task_map:
            Task.objects.filter(pk=task_map[task.pk].pk).update(
                parent=task_map[task.parent_id]
            )
    highest = Task.objects.filter(project=source).aggregate(top=Max("number"))["top"]
    TaskCounter.objects.update_or_create(
        project=copy, defaults={"next_number": (highest or 0) + 1}
    )

    comments = Comment.objects.filter(task__in=task_map.keys()).order_by("created_at")
    Comment.objects.bulk_create(
        Comment(task=task_map[c.task_id], author=owner, body=c.body) for c in comments
    )

    for note in Note.objects.filter(project=source):
        new = Note.objects.create(
            project=copy, title=note.title, body=note.body, author=owner
        )
        NoteRevision.objects.create(
            note=new, version=1, title=new.title, body=new.body, edited_by=owner
        )
        tag_service.sync(NoteTag, "note", new, tag_service.names(NoteTag, "note", note))
        TaskNote.objects.bulk_create(
            TaskNote(task=task_map[link.task_id], note=new)
            for link in TaskNote.objects.filter(note=note)
            if link.task_id in task_map
        )
