from django.db.models import F, Model

from projects.models import Tag


def names(through: type[Model], owner_field: str, owner: Model) -> list[str]:
    """Tag names attached to `owner` through a `<owner>Tag` join model."""
    return sorted(
        through.objects.filter(**{owner_field: owner}).values_list(
            "tag__name", flat=True
        )
    )


def sync(
    through: type[Model], owner_field: str, owner: Model, wanted: list[str]
) -> dict | None:
    """Make the owner's tags equal `wanted` (already normalized), keeping
    Tag.usage_count in step. Returns {"from": [...], "to": [...]} on change."""
    before = set(names(through, owner_field, owner))
    after = set(wanted)
    if before == after:
        return None
    for name in after - before:
        tag, _ = Tag.objects.get_or_create(name=name)
        through.objects.create(**{owner_field: owner, "tag": tag})
        Tag.objects.filter(pk=tag.pk).update(usage_count=F("usage_count") + 1)
    removed = through.objects.filter(
        **{owner_field: owner, "tag__name__in": before - after}
    )
    release(list(removed.values_list("tag_id", flat=True)))
    removed.delete()
    return {"from": sorted(before), "to": sorted(after)}


def release(tag_ids: list) -> None:
    """Lower usage_count for tags that lose one user each."""
    for tag_id in tag_ids:
        Tag.objects.filter(pk=tag_id, usage_count__gt=0).update(
            usage_count=F("usage_count") - 1
        )
