from django.db import transaction

from projects.models import Membership
from tracker.models import KanbanPreference


def get(membership: Membership) -> KanbanPreference:
    """The caller's saved board setup, or an unsaved default."""
    return KanbanPreference.objects.filter(
        user=membership.user, project=membership.project
    ).first() or KanbanPreference(user=membership.user, project=membership.project)


@transaction.atomic
def save(membership: Membership, *, group_by: str, sort_by: str) -> KanbanPreference:
    preference, _ = KanbanPreference.objects.update_or_create(
        user=membership.user,
        project=membership.project,
        defaults={"group_by": group_by, "sort_by": sort_by},
    )
    return preference
