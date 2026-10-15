from django.db import migrations

from tracker.constants.categories import DEFAULT_PRIORITIES, DEFAULT_STATUSES


def backfill(apps, schema_editor):
    """Projects created before this feature get the default statuses,
    priorities and a task counter."""
    Project = apps.get_model("projects", "Project")
    Status = apps.get_model("tracker", "Status")
    Priority = apps.get_model("tracker", "Priority")
    TaskCounter = apps.get_model("tracker", "TaskCounter")

    for project in Project.objects.all():
        TaskCounter.objects.get_or_create(project=project)
        if not Status.objects.filter(project=project).exists():
            for position, (name, category, is_default) in enumerate(DEFAULT_STATUSES):
                Status.objects.create(
                    project=project,
                    name=name,
                    category=category,
                    position=position,
                    is_default=is_default,
                )
        if not Priority.objects.filter(project=project).exists():
            for position, (name, is_default) in enumerate(DEFAULT_PRIORITIES):
                Priority.objects.create(
                    project=project,
                    name=name,
                    rank=position + 1,
                    position=position,
                    is_default=is_default,
                )


class Migration(migrations.Migration):
    dependencies = [("tracker", "0001_initial"), ("projects", "0001_initial")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
