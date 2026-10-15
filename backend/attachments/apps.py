from django.apps import AppConfig


class AttachmentsConfig(AppConfig):
    name = "attachments"

    def ready(self) -> None:
        from attachments import signals  # noqa: F401  (connects post_delete)
        from attachments.services import markdown
        from tracker.services import hooks

        if markdown.validate_note_images not in hooks.note_body_validators:
            hooks.note_body_validators.append(markdown.validate_note_images)
