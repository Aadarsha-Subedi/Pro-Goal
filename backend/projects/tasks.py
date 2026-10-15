from celery import shared_task

from projects.constants.tasks import DEFAULT_QUEUE


@shared_task(queue=DEFAULT_QUEUE)
def purge_deleted_projects() -> int:
    from projects.services.project_service import purge_deleted_projects as purge

    return purge()


@shared_task(queue=DEFAULT_QUEUE)
def expire_join_requests() -> int:
    from projects.services.join_service import expire_join_requests as expire

    return expire()


@shared_task(queue=DEFAULT_QUEUE)
def expire_transfers() -> int:
    from projects.services.transfer_service import expire_transfers as expire

    return expire()


@shared_task(queue=DEFAULT_QUEUE)
def purge_activity_log() -> int:
    from projects.services.activity_feed import purge_old_entries

    return purge_old_entries()
