from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from accounts.models import User
from common.exception.domain import ValidationException
from projects.constants import error_codes, messages
from projects.models import Membership, Project

# (project, leaving user, new owner or None to unassign) -> None
ReassignHandler = Callable[[Project, User, User | None], None]


@dataclass(frozen=True)
class ReassignmentEntry:
    name: str
    handler: ReassignHandler


class ReassignmentRegistry:
    """Role: every model owned by a user registers one handler here. Removing
    a member (or leaving) runs them all in the caller's transaction. Adding an
    owned model means registering one handler, nothing else changes."""

    def __init__(self) -> None:
        self._entries: dict[str, ReassignmentEntry] = {}

    def register(self, name: str, handler: ReassignHandler) -> None:
        self._entries[name] = ReassignmentEntry(name, handler)

    def names(self) -> list[str]:
        return sorted(self._entries)

    def run(
        self, project: Project, leaving: User, mapping: dict[str, UUID] | None = None
    ) -> None:
        """Move owned items per `mapping` ({name: new owner id}); names left out
        become unassigned. Call inside a transaction."""
        mapping = mapping or {}
        targets = self._validate(project, leaving, mapping)
        for entry in list(self._entries.values()):
            entry.handler(project, leaving, targets.get(entry.name))

    def _validate(
        self, project: Project, leaving: User, mapping: dict[str, UUID]
    ) -> dict[str, User]:
        unknown = [name for name in mapping if name not in self._entries]
        if unknown:
            raise ValidationException(
                messages.INVALID_REASSIGNMENT,
                errors=[
                    {
                        "field": f"reassign.{name}",
                        "message": messages.UNKNOWN_REASSIGNMENT_KEY.format(name=name),
                    }
                    for name in unknown
                ],
                error_code=error_codes.INVALID_REASSIGNMENT,
            )
        members = {
            m.user_id: m.user
            for m in Membership.objects.filter(project=project).select_related("user")
        }
        targets: dict[str, User] = {}
        for name, user_id in mapping.items():
            user = members.get(user_id)
            if user is None or user.pk == leaving.pk:
                raise ValidationException(
                    messages.INVALID_REASSIGNMENT,
                    errors=[
                        {
                            "field": f"reassign.{name}",
                            "message": messages.REASSIGNMENT_TARGET_NOT_MEMBER,
                        }
                    ],
                    error_code=error_codes.INVALID_REASSIGNMENT,
                )
            targets[name] = user
        return targets


registry = ReassignmentRegistry()
