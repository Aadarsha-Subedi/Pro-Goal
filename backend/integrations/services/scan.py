from datetime import timedelta

from django.utils import timezone

from integrations.constants import limits
from integrations.constants.events import EventType, Source
from integrations.services import outbox
from tracker.constants.categories import StatusCategory
from tracker.models import Task


def scan_due_dates() -> int:
    """Emit `task_due_soon` (due today or tomorrow) and `task_overdue` (due date
    passed) once per task and due date. Done, deleted and archived-project
    tasks are skipped. Run daily; the dedupe key makes reruns harmless."""
    today = timezone.now().date()
    horizon = today + timedelta(days=limits.DUE_SOON_DAYS)
    tasks = (
        Task.objects.filter(
            due_date__isnull=False,
            due_date__lte=horizon,
            project__is_deleted=False,
            project__archived_at__isnull=True,
        )
        .exclude(status__category=StatusCategory.DONE)
        .select_related("project")
    )
    emitted = 0
    for task in tasks:
        event_type = (
            EventType.TASK_OVERDUE if task.due_date < today else EventType.TASK_DUE_SOON
        )
        event = outbox.emit(
            task.project,
            event_type,
            {
                "project_name": task.project.name,
                "task_id": str(task.pk),
                "task_number": task.number,
                "title": task.title,
                "due_date": task.due_date.isoformat(),
            },
            source=Source.SYSTEM,
            dedupe_key=f"{event_type}:{task.pk}:{task.due_date.isoformat()}",
        )
        emitted += 1 if event else 0
    return emitted
