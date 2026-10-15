from projects.models import Project
from tracker.constants.categories import DEFAULT_PRIORITIES, DEFAULT_STATUSES
from tracker.models import Priority, Status, TaskCounter


def seed_project_defaults(project: Project) -> None:
    """Give a project its starting statuses, priorities and task counter.
    Safe to run twice: existing rows are left alone."""
    TaskCounter.objects.get_or_create(project=project)
    if not Status.objects.filter(project=project).exists():
        Status.objects.bulk_create(
            Status(
                project=project,
                name=name,
                category=category,
                position=position,
                is_default=is_default,
            )
            for position, (name, category, is_default) in enumerate(DEFAULT_STATUSES)
        )
    if not Priority.objects.filter(project=project).exists():
        Priority.objects.bulk_create(
            Priority(
                project=project,
                name=name,
                rank=position + 1,
                position=position,
                is_default=is_default,
            )
            for position, (name, is_default) in enumerate(DEFAULT_PRIORITIES)
        )
