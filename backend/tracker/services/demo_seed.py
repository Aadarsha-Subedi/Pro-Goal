"""Fills a demo project's tracker with its content. Writes models directly: the
system user owns the project and demo content has no dates."""

from django.db import transaction

from common.validators.tags import normalize_tags
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


@transaction.atomic
def seed_content(project: Project, spec: dict) -> None:
    """Replace the project's tasks and notes with the content in `spec`."""
    clear(project)
    author = project.owner
    statuses = {s.name: s for s in Status.objects.filter(project=project)}
    priorities = {p.name: p for p in Priority.objects.filter(project=project)}

    tasks: list[Task] = []
    for number, (title, description, status, priority, parent, tags) in enumerate(
        spec["tasks"], start=1
    ):
        task = Task.objects.create(
            project=project,
            number=number,
            title=title,
            description=description,
            status=statuses[status],
            priority=priorities[priority],
            parent=tasks[parent] if parent is not None else None,
            created_by=author,
        )
        tag_service.sync(TaskTag, "task", task, normalize_tags(tags))
        tasks.append(task)
    TaskCounter.objects.update_or_create(
        project=project, defaults={"next_number": len(tasks) + 1}
    )

    for index, body in spec.get("comments", []):
        Comment.objects.create(task=tasks[index], author=author, body=body)

    for title, body in spec.get("notes", []):
        note = Note.objects.create(
            project=project, title=title, body=body, author=author
        )
        NoteRevision.objects.create(
            note=note, version=1, title=title, body=body, edited_by=author
        )


def clear(project: Project) -> None:
    """Remove all tasks and notes (and release their tags)."""
    for through, owner_field, model in (
        (TaskTag, "task", Task),
        (NoteTag, "note", Note),
    ):
        for owner in model_all(model).filter(project=project):
            tag_service.sync(through, owner_field, owner, [])
    TaskNote.objects.filter(note__project=project).delete()
    model_all(Task).filter(project=project).delete()
    Note.objects.filter(project=project).delete()


def model_all(model):
    return getattr(model, "all_objects", model.objects)
