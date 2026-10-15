import secrets

from django.db import IntegrityError, transaction

from projects.constants import fields
from projects.models import Project


def generate() -> str:
    return "".join(
        secrets.choice(fields.JOIN_CODE_ALPHABET)
        for _ in range(fields.JOIN_CODE_LENGTH)
    )


def normalize(raw: str) -> str:
    return raw.strip().upper()


def save_with_unique_code(project: Project) -> Project:
    """Save `project` with a fresh unique join code. The unique constraint is
    the arbiter: on a collision pick another code and retry."""
    for _ in range(fields.JOIN_CODE_MAX_ATTEMPTS):
        project.join_code = generate()
        try:
            with transaction.atomic():
                project.save()
            return project
        except IntegrityError:
            if not Project.all_objects.filter(join_code=project.join_code).exists():
                raise
    raise RuntimeError("Could not generate a unique join code.")
