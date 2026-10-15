from django.db import migrations

# Frozen copy: the permissions every non-owner member effectively had before
# real grants existed. Migrations must not follow later changes to the code.
CONTRIBUTOR = [
    "task.create",
    "task.title.change",
    "task.description.change",
    "task.status.change",
    "task.priority.change",
    "task.assignees.change",
    "task.start_date.change",
    "task.due_date.change",
    "task.tags.change",
    "task.parent.change",
    "note.create",
    "note.title.change",
    "note.body.change",
    "note.tags.change",
    "note.link.change",
    "comment.create",
    "attachment.create",
]


def backfill(apps, schema_editor):
    Membership = apps.get_model("projects", "Membership")
    MemberPermission = apps.get_model("projects", "MemberPermission")
    existing = set(MemberPermission.objects.values_list("membership_id", "code"))
    rows = [
        MemberPermission(membership_id=membership_id, code=code)
        for membership_id in Membership.objects.filter(is_owner=False).values_list(
            "pk", flat=True
        )
        for code in CONTRIBUTOR
        if (membership_id, code) not in existing
    ]
    MemberPermission.objects.bulk_create(rows, batch_size=1000)


class Migration(migrations.Migration):
    dependencies = [("projects", "0002_member_permission")]

    operations = [migrations.RunPython(backfill, migrations.RunPython.noop)]
