"""Copy a shared demo project into a project the caller owns."""

from django.db import transaction

from common.exception.domain import ConflictException
from projects.constants import error_codes, fields, limits, messages
from projects.models import Membership, Project
from projects.services import hooks, project_service


@transaction.atomic
def copy_project(
    membership: Membership, name: str | None = None, ip: str | None = None
) -> Membership:
    source = membership.project
    if not source.is_demo:
        raise ConflictException(
            messages.COPY_NOT_ALLOWED, error_code=error_codes.COPY_NOT_ALLOWED
        )
    user = membership.user
    held = Project.objects.filter(owner=user, copied_from__isnull=False).count()
    if held >= limits.MAX_PROJECT_COPIES_PER_USER:
        raise ConflictException(
            messages.COPY_LIMIT_REACHED.format(
                limit=limits.MAX_PROJECT_COPIES_PER_USER
            ),
            error_code=error_codes.COPY_LIMIT_REACHED,
        )
    name = (name or f"{source.name} (copy)").strip()[: fields.PROJECT_NAME_MAX_LENGTH]
    created = project_service.create(
        user,
        name=name,
        task_key=source.task_key,
        description=source.description,
        tags=project_service.tag_names(source),
        ip=ip,
    )
    copy = created.project
    copy.copied_from = source
    copy.save(update_fields=["copied_from", "updated_at"])
    hooks.run_project_copied(source, copy)
    return created
