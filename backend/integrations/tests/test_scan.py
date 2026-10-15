from datetime import timedelta

from django.utils import timezone

from integrations.models import OutboxEvent
from integrations.services import scan
from integrations.tasks import scan_due_dates
from integrations.tests.base import IntegrationTestCase
from tracker.models import Task


class DueDateScanTests(IntegrationTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.today = timezone.now().date()

    def task(self, title: str, days: int | None, **extra) -> dict:
        due = None if days is None else str(self.today + timedelta(days=days))
        return self.create_task(title, due_date=due, **extra)

    def events(self) -> dict[str, str]:
        return {
            e.payload["title"]: e.event_type
            for e in OutboxEvent.objects.filter(
                event_type__in=["task_due_soon", "task_overdue"]
            )
        }

    def test_due_soon_overdue_and_nothing_else(self):
        self.task("yesterday", -1)
        self.task("today", 0)
        self.task("tomorrow", 1)
        self.task("in three days", 3)
        self.task("no date", None)
        self.assertEqual(scan.scan_due_dates(), 3)
        self.assertEqual(
            self.events(),
            {
                "yesterday": "task_overdue",
                "today": "task_due_soon",
                "tomorrow": "task_due_soon",
            },
        )
        event = OutboxEvent.objects.get(event_type="task_overdue")
        self.assertEqual(event.source, "system")
        self.assertEqual(event.payload["due_date"], str(self.today - timedelta(days=1)))

    def test_running_again_adds_nothing(self):
        self.task("today", 0)
        self.assertEqual(scan.scan_due_dates(), 1)
        self.assertEqual(scan.scan_due_dates(), 0)
        self.assertEqual(scan_due_dates.delay().get(), 0)

    def test_a_changed_due_date_can_alert_again(self):
        created = self.task("moves", 0)
        scan.scan_due_dates()
        self.patch(
            self.url(f"tasks/{created['number']}/"),
            {"due_date": str(self.today + timedelta(days=1))},
        )
        self.assertEqual(scan.scan_due_dates(), 1)
        self.assertEqual(
            OutboxEvent.objects.filter(event_type="task_due_soon").count(), 2
        )

    def test_done_deleted_and_archived_are_skipped(self):
        done = self.task("finished", -2)
        self.patch(
            self.url(f"tasks/{done['number']}/"), {"status": self.status_id("Done")}
        )
        gone = self.task("deleted", -2)
        self.delete(self.url(f"tasks/{gone['number']}/"))
        self.task("kept", -2)
        self.assertEqual(scan.scan_due_dates(), 1)
        self.assertEqual(list(self.events()), ["kept"])

        other = self.create_project(name="Other", task_key="OTH")
        self.post(
            f"/api/projects/{other['id']}/tasks/",
            {"title": "archived one", "due_date": str(self.today - timedelta(days=3))},
        )
        self.post(f"/api/projects/{other['id']}/archive/")
        self.assertEqual(scan.scan_due_dates(), 0)

    def test_a_scan_event_reaches_the_provider(self):
        self.task("today", 0)
        scan.scan_due_dates()
        self.run_dispatch()
        sent = [p for p in self.provider.delivered if p["event"] == "task_due_soon"]
        self.assertEqual([p["title"] for p in sent], ["today"])

    def test_assignee_is_part_of_the_task_not_the_event(self):
        self.task("assigned", 0, assignees=[self.user_id("bob@example.com")])
        scan.scan_due_dates()
        event = OutboxEvent.objects.get(event_type="task_due_soon")
        self.assertNotIn("assignee_id", event.payload)
        self.assertEqual(Task.objects.count(), 1)
