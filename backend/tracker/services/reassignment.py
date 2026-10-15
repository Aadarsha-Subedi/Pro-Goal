from accounts.models import User
from projects.models import Project
from projects.services.reassignment import ReassignmentRegistry
from tracker.models import Note, TaskAssignee

TASKS = "tasks"
NOTES = "notes"


def _reassign_tasks(project: Project, leaving: User, to: User | None) -> None:
    """Hand the leaving member's assignments to `to`, or unassign them."""
    assignments = TaskAssignee.objects.filter(task__project=project, user=leaving)
    if to is not None:
        already = TaskAssignee.objects.filter(
            task__project=project, user=to
        ).values_list("task_id", flat=True)
        assignments.exclude(task_id__in=list(already)).update(user=to)
    assignments.delete()


def _reassign_notes(project: Project, leaving: User, to: User | None) -> None:
    """Notes keep their author unless a new one is chosen."""
    if to is not None:
        Note.objects.filter(project=project, author=leaving).update(author=to)


def register(registry: ReassignmentRegistry) -> None:
    registry.register(TASKS, _reassign_tasks)
    registry.register(NOTES, _reassign_notes)
