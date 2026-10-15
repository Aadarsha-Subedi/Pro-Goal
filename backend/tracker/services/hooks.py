from collections.abc import Callable

from projects.models import Project

# Other features register checks that run on every note body before it is saved
# (attachments uses this to restrict markdown images to project attachments).
NoteBodyValidator = Callable[[Project, str], None]
note_body_validators: list[NoteBodyValidator] = []


def validate_note_body(project: Project, body: str) -> None:
    for validator in note_body_validators:
        validator(project, body)
