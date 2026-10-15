from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from attachments.models import Attachment
from attachments.services import quota_service
from attachments.services.storage import storage


@receiver(post_delete, sender=Attachment)
def release_attachment(sender, instance: Attachment, **kwargs) -> None:
    """Whatever deletes an attachment row (the API, a task purge, a project
    purge) frees its quota and removes the R2 object after commit."""
    quota_service.release(
        instance.project_id, instance.uploaded_by_id, instance.size_bytes
    )
    key = instance.object_key
    transaction.on_commit(lambda: storage().delete(key))
