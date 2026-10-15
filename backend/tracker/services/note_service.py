from uuid import UUID

from django.db import transaction
from django.db.models import QuerySet

from common.exception.domain import (
    PayloadTooLargeException,
    StaleDataException,
)
from common.validators.tags import normalize_tags, validate_tag_count
from projects import permissions
from projects.constants import permissions as codes
from projects.models import Membership
from projects.services import access as project_access
from projects.services import activity, tag_service
from tracker.constants import actions, error_codes, fields, messages
from tracker.models import Note, NoteRevision, NoteTag, Task, TaskNote
from tracker.services import access, hooks, mention_service

NOTE_FIELD_PERMISSIONS = {
    "title": codes.NOTE_TITLE_CHANGE,
    "body": codes.NOTE_BODY_CHANGE,
    "tags": codes.NOTE_TAGS_CHANGE,
}


def _check_body(project, body: str) -> None:
    if len(body.encode()) > fields.NOTE_BODY_MAX_BYTES:
        raise PayloadTooLargeException(
            messages.NOTE_TOO_LARGE, error_code=error_codes.NOTE_TOO_LARGE
        )
    hooks.validate_note_body(project, body)


def _tags(names: list[str]) -> list[str]:
    cleaned = normalize_tags(names)
    validate_tag_count(cleaned, fields.MAX_TAGS_PER_ITEM)
    return cleaned


def list_notes(
    membership: Membership, *, q: str | None = None, tag: str | None = None
) -> QuerySet[Note]:
    queryset = Note.objects.filter(project=membership.project).select_related("author")
    if q:
        queryset = queryset.filter(title__icontains=q.strip())
    if tag:
        queryset = queryset.filter(note_tags__tag__name=tag.strip().lower())
    return queryset.prefetch_related("note_tags__tag").distinct()


def notes_for_task(task: Task) -> QuerySet[Note]:
    return (
        Note.objects.filter(task_notes__task=task)
        .select_related("author")
        .prefetch_related("note_tags__tag")
    )


def _revision(note: Note, editor) -> None:
    NoteRevision.objects.create(
        note=note,
        version=note.version,
        title=note.title,
        body=note.body,
        edited_by=editor,
    )


@transaction.atomic
def create(
    membership: Membership,
    *,
    title: str,
    body: str = "",
    tags: list[str] | None = None,
    ip: str | None = None,
) -> Note:
    permissions.require_permission(membership, codes.NOTE_CREATE)
    project = membership.project
    project_access.ensure_writable(project)
    _check_body(project, body)
    names = _tags(tags or [])
    note = Note.objects.create(
        project=project, title=title.strip(), body=body, author=membership.user
    )
    _revision(note, membership.user)
    tag_service.sync(NoteTag, "note", note, names)
    mention_service.notify_new_mentions(
        project,
        membership.user,
        old_body="",
        new_body=body,
        where=f"the note “{note.title}”",
        path=f"notes/{note.pk}",
    )
    activity.log(
        project,
        membership.user,
        actions.NOTE_CREATED,
        actions.ENTITY_NOTE,
        note.pk,
        {"title": note.title},
        ip,
    )
    return note


@transaction.atomic
def update(
    membership: Membership,
    note_id: UUID,
    data: dict,
    ip: str | None = None,
) -> Note:
    """`data["version"]` is the version the editor started from; a mismatch
    means someone saved in between and the edit is refused."""
    project = membership.project
    project_access.ensure_writable(project)
    data = dict(data)
    version = data.pop("version")
    permissions.require_fields(
        membership, [(name, NOTE_FIELD_PERMISSIONS[name]) for name in data]
    )
    note = (
        Note.objects.select_for_update(of=("self",))
        .select_related("project", "author")
        .filter(project=project, pk=note_id)
        .first()
    ) or access.get_note(membership, note_id)
    if note.version != version:
        raise StaleDataException(messages.STALE_NOTE, error_code=error_codes.STALE_NOTE)

    changes: dict = {}
    old_body = note.body
    if "title" in data and data["title"].strip() != note.title:
        changes["title"] = {"from": note.title, "to": data["title"].strip()}
        note.title = data["title"].strip()
    if "body" in data and data["body"] != note.body:
        _check_body(project, data["body"])
        changes["body"] = {"changed": True}
        note.body = data["body"]
    content_changed = bool(changes)
    if content_changed:
        note.version += 1
        note.save()
        _revision(note, membership.user)
    if "tags" in data and (
        diff := tag_service.sync(NoteTag, "note", note, _tags(data["tags"]))
    ):
        changes["tags"] = diff
        if not content_changed:
            note.save(update_fields=["updated_at"])
    if "body" in changes:
        mention_service.notify_new_mentions(
            project,
            membership.user,
            old_body=old_body,
            new_body=note.body,
            where=f"the note “{note.title}”",
            path=f"notes/{note.pk}",
        )
    if changes:
        activity.log(
            project,
            membership.user,
            actions.NOTE_UPDATED,
            actions.ENTITY_NOTE,
            note.pk,
            changes,
            ip,
        )
    return note


@transaction.atomic
def delete(membership: Membership, note_id: UUID, ip: str | None = None) -> None:
    note = access.get_note(membership, note_id)
    permissions.require_permission(membership, codes.NOTE_DELETE)
    project_access.ensure_writable(membership.project)
    tag_service.release(
        list(NoteTag.objects.filter(note=note).values_list("tag_id", flat=True))
    )
    activity.log(
        membership.project,
        membership.user,
        actions.NOTE_DELETED,
        actions.ENTITY_NOTE,
        note.pk,
        {"title": note.title},
        ip,
    )
    note.delete()


def revisions(membership: Membership, note_id: UUID) -> QuerySet[NoteRevision]:
    note = access.get_note(membership, note_id)
    return NoteRevision.objects.filter(note=note).select_related("edited_by")


@transaction.atomic
def link(
    membership: Membership, task: Task, note_id: UUID, ip: str | None = None
) -> Note:
    permissions.require_permission(membership, codes.NOTE_LINK_CHANGE)
    project_access.ensure_writable(membership.project)
    note = access.get_note(membership, note_id)
    _, created = TaskNote.objects.get_or_create(task=task, note=note)
    if created:
        activity.log(
            membership.project,
            membership.user,
            actions.NOTE_LINKED,
            actions.ENTITY_TASK,
            task.pk,
            {"note": str(note.pk)},
            ip,
        )
    return note


@transaction.atomic
def unlink(
    membership: Membership, task: Task, note_id: UUID, ip: str | None = None
) -> None:
    permissions.require_permission(membership, codes.NOTE_LINK_CHANGE)
    project_access.ensure_writable(membership.project)
    note = access.get_note(membership, note_id)
    removed, _ = TaskNote.objects.filter(task=task, note=note).delete()
    if removed:
        activity.log(
            membership.project,
            membership.user,
            actions.NOTE_UNLINKED,
            actions.ENTITY_TASK,
            task.pk,
            {"note": str(note.pk)},
            ip,
        )
