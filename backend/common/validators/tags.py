from common.exception.domain import ValidationException
from common.validators.constants import TOO_MANY_TAGS_MESSAGE


def normalize_tags(names: list[str]) -> list[str]:
    """Trim and lowercase tag names, drop blanks and duplicates, keep order."""
    seen: dict[str, None] = {}
    for name in names:
        cleaned = name.strip().lower()
        if cleaned:
            seen[cleaned] = None
    return list(seen)


def validate_tag_count(tags: list[str], limit: int, field: str = "tags") -> None:
    """Raise an API ValidationException on `field` when there are more than
    `limit` tags."""
    if len(tags) > limit:
        raise ValidationException(
            errors=[
                {"field": field, "message": TOO_MANY_TAGS_MESSAGE.format(limit=limit)}
            ]
        )
