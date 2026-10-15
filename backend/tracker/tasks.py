from celery import shared_task

from tracker.constants.tasks import DEFAULT_QUEUE


@shared_task(queue=DEFAULT_QUEUE)
def purge_deleted_tasks() -> int:
    from tracker.services.task_service import purge_deleted_tasks as purge

    return purge()
