from collections.abc import Callable
from uuid import UUID

from accounts.models import User
from projects.models import ActivityLog, Project

# Features register a callable run, inside the same transaction, for every
# activity row written (integrations turn them into outbox events this way).
ActivityListener = Callable[[ActivityLog], None]
listeners: list[ActivityListener] = []


def log(
    project: Project,
    actor: User | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    changes: dict | None = None,
    ip: str | None = None,
) -> ActivityLog:
    """Append one row to the project's activity log."""
    row = ActivityLog.objects.create(
        project=project,
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changes=changes or {},
        ip=ip,
    )
    for listener in listeners:
        listener(row)
    return row
