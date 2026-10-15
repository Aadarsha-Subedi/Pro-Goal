from datetime import timedelta

from django.core import mail
from django.utils import timezone

from integrations.models import NotificationPreference, OutboxEvent
from integrations.services import audience, scan
from integrations.tests.base import IntegrationTestCase


class EmailNotificationTests(IntegrationTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.bob = self.user_id("bob@example.com")
        self.owner = self.user_id("owner@example.com")
        mail.outbox.clear()

    def opt_in(self, user_id: str, *events: str) -> None:
        for event in events:
            NotificationPreference.objects.update_or_create(
                user_id=user_id, event_type=event, defaults={"email": True}
            )

    def mails_to(self, address: str) -> list:
        return [m for m in mail.outbox if m.to == [address]]

    def test_nothing_is_sent_until_a_person_opts_in(self):
        self.create_task("Quiet", assignees=[self.bob])
        self.assertEqual(self.mails_to("bob@example.com"), [])

    def test_assigned_email_has_the_safe_content_and_one_copy(self):
        self.opt_in(self.bob, "task_assigned")
        task = self.create_task(
            "Fix login",
            assignees=[self.bob],
            due_date="2031-02-03",
            description="TOP SECRET",
        )
        sent = self.mails_to("bob@example.com")
        self.assertEqual(len(sent), 1)
        message = sent[0]
        self.assertIn("Task assigned to Bob", message.subject)
        self.assertIn("APL-1", message.subject)
        self.assertIn("Fix login", message.body)
        self.assertIn("Status: To do", message.body)
        self.assertIn("Assignees: Bob", message.body)
        self.assertIn("Due: 2031-02-03", message.body)
        self.assertIn(f"/projects/{self.pid}/tasks/{task['number']}", message.body)
        self.assertNotIn("TOP SECRET", message.body)
        self.assertNotIn("@example.com", message.body)

    def test_only_opted_in_events_and_never_the_actor(self):
        self.opt_in(self.bob, "task_assigned")
        self.opt_in(self.owner, "task_assigned")
        self.switch("bob@example.com")
        self.create_task("Self assigned", assignees=[self.bob])
        self.assertEqual(self.mails_to("bob@example.com"), [])  # the actor
        self.switch("owner@example.com")
        task = self.create_task("For Bob", assignees=[self.bob])
        self.assertEqual(len(self.mails_to("bob@example.com")), 1)
        self.assertEqual(self.mails_to("owner@example.com"), [])  # the actor
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "hi"})
        self.assertEqual(
            len(self.mails_to("bob@example.com")), 1
        )  # comments not opted in

    def test_comment_email_has_no_comment_text(self):
        self.opt_in(self.bob, "comment_added")
        task = self.create_task("Shared", assignees=[self.bob])
        mail.outbox.clear()
        self.post(
            self.url(f"tasks/{task['number']}/comments/"),
            {"body": "PRIVATE COMMENT TEXT"},
        )
        sent = self.mails_to("bob@example.com")
        self.assertEqual(len(sent), 1)
        self.assertIn("commented on a task", sent[0].subject)
        self.assertNotIn("PRIVATE COMMENT", sent[0].subject + sent[0].body)

    def test_join_request_goes_to_the_owner_and_approvers(self):
        self.opt_in(self.owner, "join_request_created")
        self.opt_in(self.bob, "join_request_created")  # Bob cannot approve
        self.make_user("carl@example.com")
        mail.outbox.clear()
        self.join(self.project, "carl@example.com")
        subjects = [m.subject for m in self.mails_to("owner@example.com")]
        self.assertTrue(any("asked to join" in s for s in subjects))
        self.assertEqual(
            [
                m
                for m in self.mails_to("bob@example.com")
                if "asked to join" in m.subject
            ],
            [],
        )
        self.switch("owner@example.com")
        self.put(
            self.url(f"members/{self.bob}/permissions/"),
            {"permissions": ["member.approve"]},
        )
        mail.outbox.clear()
        self.make_user("dave@example.com")
        self.join(self.project, "dave@example.com")
        self.assertTrue(
            [
                m
                for m in self.mails_to("bob@example.com")
                if "asked to join" in m.subject
            ]
        )

    def test_due_dates_email_the_assignees(self):
        self.opt_in(self.bob, "task_due_soon", "task_overdue")
        today = timezone.now().date()
        self.create_task(
            "Soon", due_date=str(today + timedelta(days=1)), assignees=[self.bob]
        )
        self.create_task(
            "Late", due_date=str(today - timedelta(days=2)), assignees=[self.bob]
        )
        mail.outbox.clear()
        scan.scan_due_dates()
        self.run_dispatch()
        subjects = sorted(
            m.subject.split(":")[0] for m in self.mails_to("bob@example.com")
        )
        self.assertEqual(subjects, ["Task due soon", "Task overdue"])

    def test_people_who_left_the_project_get_nothing(self):
        self.opt_in(self.bob, "comment_added")
        task = self.create_task("Bob's", assignees=[self.bob])
        self.delete(self.url(f"members/{self.bob}/"))
        mail.outbox.clear()
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "hello"})
        self.assertEqual(self.mails_to("bob@example.com"), [])

    def test_redispatching_an_event_does_not_send_twice(self):
        self.opt_in(self.bob, "task_assigned")
        self.create_task("Once", assignees=[self.bob])
        OutboxEvent.objects.filter(event_type="task_assigned").update(
            dispatched_at=None
        )
        self.run_dispatch()
        self.run_dispatch()
        self.assertEqual(len(self.mails_to("bob@example.com")), 1)

    def test_works_without_any_integration(self):
        from integrations.models import Integration

        Integration.objects.all().delete()
        self.opt_in(self.bob, "task_assigned")
        self.create_task("No Slack here", assignees=[self.bob])
        self.assertEqual(len(self.mails_to("bob@example.com")), 1)

    def test_slack_and_email_share_the_same_audience(self):
        task = self.create_task("Shared", assignees=[self.bob])
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "x"})
        event = OutboxEvent.objects.filter(event_type="comment_added").latest(
            "created_at"
        )
        expected = audience.candidate_users(event)
        self.assertEqual(
            expected, {self.bob}
        )  # the owner commented, Bob is the assignee
        self.assertIn("comment_added", [e.value for e in audience.PERSONAL_EVENTS])

    def test_preferences_endpoint_reports_the_email_flag(self):
        response = self.put(
            "/api/me/notification-preferences/",
            {"preferences": {"task_assigned": {"email": True}}},
        )
        values = {i["event_type"]: i["email"] for i in response.json()["data"]["items"]}
        self.assertTrue(values["task_assigned"])
        self.assertFalse(values["comment_added"])
