from django.db import migrations
from django.db.models import F


def backfill(apps, schema_editor):
    """Projects that were already listed get a listing time so the explore
    page can order them."""
    Project = apps.get_model("projects", "Project")
    Project.objects.filter(is_listed=True, listed_at__isnull=True).update(
        listed_at=F("updated_at")
    )


class Migration(migrations.Migration):
    dependencies = [("projects", "0004_project_listed_at")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
