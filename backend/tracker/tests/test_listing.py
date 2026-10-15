from datetime import timedelta

from django.utils import timezone

from tracker.tests.base import TrackerTestCase


class ListingTests(TrackerTestCase):
    def setUp(self) -> None:
        super().setUp()
        today = timezone.now().date()
        self.bob = self.user_id("bob@example.com")
        self.a = self.create_task(
            "Alpha login bug",
            due_date=str(today - timedelta(days=2)),
            tags=["bug"],
            assignees=[self.bob],
            priority=self.priority_id("Urgent"),
        )
        self.b = self.create_task(
            "Beta report",
            due_date=str(today + timedelta(days=5)),
            tags=["docs"],
            status=self.status_id("In progress"),
        )
        self.c = self.create_task("Gamma cleanup", status=self.status_id("Done"))
        self.sub = self.post(
            self.url(f"tasks/{self.b['number']}/subtasks/"), {"title": "Beta sub"}
        ).json()["data"]

    def titles(self, **params) -> list[str]:
        return [t["title"] for t in self.items("tasks/", **params)]

    def test_default_order_is_newest_first_and_lists_skip_description(self):
        self.assertEqual(self.titles()[0], "Beta sub")
        self.assertNotIn("description", self.items("tasks/")[0])

    def test_filters(self):
        self.assertEqual(
            self.titles(status=self.status_id("In progress")), ["Beta report"]
        )
        self.assertEqual(
            self.titles(priority=self.priority_id("Urgent")), ["Alpha login bug"]
        )
        self.assertEqual(self.titles(assignee=self.bob), ["Alpha login bug"])
        self.assertEqual(self.titles(tag="BUG"), ["Alpha login bug"])
        self.assertEqual(self.titles(q="report"), ["Beta report"])
        self.assertEqual(self.titles(q="BETA", top_level="true"), ["Beta report"])
        today = timezone.now().date()
        self.assertEqual(self.titles(due_date_before=today), ["Alpha login bug"])

    def test_overdue(self):
        self.assertEqual(self.titles(overdue="true"), ["Alpha login bug"])
        flagged = {t["title"]: t["is_overdue"] for t in self.items("tasks/")}
        self.assertTrue(flagged["Alpha login bug"])
        self.assertFalse(flagged["Beta report"])
        # A Done task is never overdue.
        past = str(timezone.now().date() - timedelta(days=9))
        self.patch(self.url(f"tasks/{self.c['number']}/"), {"due_date": past})
        self.assertEqual(self.titles(overdue="true"), ["Alpha login bug"])

    def test_ordering_and_server_time(self):
        self.assertEqual(
            self.titles(ordering="number", top_level="true"),
            ["Alpha login bug", "Beta report", "Gamma cleanup"],
        )
        self.assertEqual(self.titles(ordering="-priority")[0], "Alpha login bug")
        # Missing due dates sort last in both directions.
        self.assertEqual(self.titles(ordering="due_date")[0], "Alpha login bug")
        self.assertEqual(self.titles(ordering="-due_date")[0], "Beta report")
        bad = self.get(self.url("tasks/?ordering=nope"))
        self.assertEqual(bad.json()["code"], "invalid_sort")
        meta = self.get(self.url("tasks/")).json()["meta"]
        self.assertIn("server_time", meta)
        self.assertEqual(meta["server_date"], timezone.now().date().isoformat())

    def test_pagination_and_bad_filter(self):
        response = self.get(self.url("tasks/?limit=2"))
        self.assertEqual(len(response.json()["data"]["items"]), 2)
        self.assertEqual(response.json()["meta"]["count"], 4)
        self.assertEqual(
            self.get(self.url("tasks/?status=not-a-uuid")).status_code, 400
        )

    def test_my_tasks_spans_projects(self):
        other = self.create_project(name="Other", task_key="OTH")
        self.post(
            f"/api/projects/{other['id']}/tasks/",
            {"title": "Solo", "assignees": [self.user_id("owner@example.com")]},
        )
        self.post(
            self.url("tasks/"),
            {"title": "Mine", "assignees": [self.user_id("owner@example.com")]},
        )
        mine = self.get("/api/me/tasks/").json()["data"]["items"]
        self.assertEqual(sorted(t["title"] for t in mine), ["Mine", "Solo"])
        self.switch("bob@example.com")
        bobs = self.get("/api/me/tasks/").json()["data"]["items"]
        self.assertEqual([t["title"] for t in bobs], ["Alpha login bug"])
        # Deleted tasks drop out.
        self.switch("owner@example.com")
        self.delete(self.url(f"tasks/{self.a['number']}/"))
        self.switch("bob@example.com")
        self.assertEqual(self.get("/api/me/tasks/").json()["data"]["items"], [])
