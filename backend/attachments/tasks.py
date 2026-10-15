from celery import shared_task

from attachments.constants.tasks import DEFAULT_QUEUE


@shared_task(queue=DEFAULT_QUEUE)
def process_image(attachment_id: str) -> None:
    from attachments.services import image_service

    image_service.process(attachment_id)


@shared_task(queue=DEFAULT_QUEUE)
def cleanup_pending_attachments() -> int:
    from attachments.services import attachment_service

    return attachment_service.cleanup_pending()


@shared_task(queue=DEFAULT_QUEUE)
def recompute_storage_usage() -> int:
    """Repair counters that drifted (for example after a crash between a file
    change and its counter update)."""
    from attachments.models import ProjectStorageUsage, UserStorageUsage
    from attachments.services import quota_service

    count = 0
    for project_id in ProjectStorageUsage.objects.values_list("pk", flat=True):
        quota_service.recompute_project(project_id)
        count += 1
    for user_id in UserStorageUsage.objects.values_list("pk", flat=True):
        quota_service.recompute_user(user_id)
        count += 1
    return count
