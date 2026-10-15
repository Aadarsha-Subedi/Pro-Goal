"""Rules shared by statuses and priorities (both are ordered, named, per-project
lists with one default)."""

from django.db import models
from django.db.models.functions import Lower

from common.exception.domain import ConflictException, ValidationException
from projects.models import Project
from tracker.constants import error_codes, messages


def ensure_unique_name(
    model: type[models.Model], project: Project, name: str, exclude_pk=None
) -> None:
    clash = model.objects.filter(project=project).annotate(_lower=Lower("name"))
    clash = clash.filter(_lower=name.lower())
    if exclude_pk is not None:
        clash = clash.exclude(pk=exclude_pk)
    if clash.exists():
        raise ValidationException(
            errors=[{"field": "name", "message": messages.DUPLICATE_NAME}],
            error_code=error_codes.DUPLICATE_NAME,
        )


def next_position(model: type[models.Model], project: Project) -> int:
    last = model.objects.filter(project=project).order_by("-position").first()
    return last.position + 1 if last else 0


def move(
    model: type[models.Model], project: Project, item: models.Model, position: int
) -> None:
    """Put `item` at `position` and renumber its siblings 0..n-1."""
    siblings = list(
        model.objects.filter(project=project).exclude(pk=item.pk).order_by("position")
    )
    siblings.insert(max(0, min(position, len(siblings))), item)
    for index, sibling in enumerate(siblings):
        if sibling.position != index or hasattr(sibling, "rank"):
            sibling.position = index
            if hasattr(sibling, "rank"):
                sibling.rank = index + 1
            sibling.save(update_fields=_order_fields(sibling))


def _order_fields(item: models.Model) -> list[str]:
    fields = ["position", "updated_at"]
    if hasattr(item, "rank"):
        fields.append("rank")
    return fields


def make_default(
    model: type[models.Model], project: Project, item: models.Model
) -> None:
    model.objects.filter(project=project, is_default=True).exclude(pk=item.pk).update(
        is_default=False
    )
    if not item.is_default:
        item.is_default = True
        item.save(update_fields=["is_default", "updated_at"])


def ensure_deletable(item: models.Model) -> None:
    if item.is_default:
        raise ConflictException(
            messages.CANNOT_DELETE_DEFAULT, error_code=error_codes.CANNOT_DELETE_DEFAULT
        )


def replacement_for(
    model: type[models.Model], item: models.Model, replacement_id, in_use: bool
) -> models.Model | None:
    """The item that inherits the deleted one's tasks, or None if unused."""
    if not in_use:
        return None
    if replacement_id is None:
        raise ConflictException(
            messages.IN_USE_NEEDS_REPLACEMENT,
            error_code=error_codes.IN_USE_NEEDS_REPLACEMENT,
        )
    replacement = (
        model.objects.filter(project_id=item.project_id, pk=replacement_id)
        .exclude(pk=item.pk)
        .first()
    )
    if replacement is None:
        raise ValidationException(
            errors=[{"field": "move_to", "message": messages.INVALID_REPLACEMENT}],
            error_code=error_codes.INVALID_REPLACEMENT,
        )
    return replacement
