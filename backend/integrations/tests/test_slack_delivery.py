from django.core import mail

from integrations.context import use_source
from integrations.models import DeliveryAttempt, NotificationPreference, OutboxEvent
from integrations.services import delivery as delivery_service
from integrations.tests.slack_base import TEAM, TOKEN, SlackTestCase, api_error

ALL_PERSONAL = [
    "task_assigned",
    "task_due_soon",
    "task_overdue",
    "comment_added",
    "join_request_created",
]


class ChannelPostTests(SlackTestCase):
    def texts(self) -> list[str]:
        return [post["text"] for post in self.hub.posts]

    def test_a_mapped_channel_gets_enabled_events_only(self):
        self.map_channel("C1", ["task_created"])
        task = self.create_task("Ship the release")
        self.assertEqual(len(self.hub.posts), 1)
        post = self.hub.posts[0]
        self.assertEqual((post["channel"], post["token"]), ("C1", TOKEN))
        self.assertIn("APL-1 Ship the release", post["text"])
        # An event the channel did not ask for is not posted.
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "hello"})
        self.assertEqual(len(self.hub.posts), 1)

    def test_every_mapped_channel_with_the_event_on_gets_its_own_message(self):
        self.map_channel("C1", ["task_created"])
        self.map_channel("C2", ["task_created", "comment_added"])
        self.create_task("One")
        self.assertEqual(sorted(p["channel"] for p in self.hub.posts), ["C1", "C2"])
        deliveries = DeliveryAttempt.objects.values_list("target", flat=True)
        self.assertEqual(sorted(deliveries), ["channel:C1", "channel:C2"])

    def test_no_mapping_means_no_posts(self):
        self.create_task("Nobody listens")
        self.assertEqual(self.hub.posts, [])

    def test_changes_made_from_slack_are_not_posted_back(self):
        self.map_channel("C1", ["task_created"])
        with use_source("slack"):
            self.create_task("From a slash command")
        self.assertEqual(self.hub.posts, [])
        self.create_task("From the web")
        self.assertEqual(len(self.hub.posts), 1)

    def test_messages_never_carry_descriptions_comments_or_emails(self):
        self.map_channel(
            "C1",
            ["task_created", "task_updated", "comment_added", "join_request_created"],
        )
        task = self.create_task(
            "Plan",
            description="TOP SECRET DESCRIPTION",
            assignees=[self.user_id("bob@example.com")],
        )
        self.patch(
            self.url(f"tasks/{task['number']}/"),
            {"description": "ANOTHER SECRET", "title": "Plan v2"},
        )
        self.post(
            self.url(f"tasks/{task['number']}/comments/"),
            {"body": "PRIVATE COMMENT TEXT"},
        )
        self.make_user("carl@example.com")
        self.join(self.project, "carl@example.com")
        everything = str(self.hub.posts)
        for secret in (
            "TOP SECRET",
            "ANOTHER SECRET",
            "PRIVATE COMMENT",
            "@example.com",
        ):
            self.assertNotIn(secret, everything)
        self.assertIn("description", everything)  # the field is named, not quoted
        self.assertGreaterEqual(len(self.hub.posts), 4)

    def test_update_message_shows_status_and_due_date_changes_and_links(self):
        self.map_channel("C1", ["task_updated"])
        task = self.create_task("Plan")
        self.patch(
            self.url(f"tasks/{task['number']}/"),
            {"status": self.status_id("In progress"), "due_date": "2031-02-03"},
        )
        text = " ".join(str(p["blocks"]) for p in self.hub.posts)
        self.assertIn("To do → In progress", text)
        self.assertIn(
            f"http://localhost:3000/projects/{self.pid}/tasks/{task['number']}", text
        )
        self.assertIn("2031-02-03", text)

    def test_markup_in_titles_is_escaped(self):
        self.map_channel("C1", ["task_created"])
        self.create_task("<!channel> a & b")
        text = str(self.hub.posts[0]["blocks"])
        self.assertNotIn("<!channel>", text)
        self.assertIn("&lt;!channel&gt; a &amp; b", text)

    def test_member_and_project_events(self):
        self.map_channel("C1", ["member_removed", "project_archived"])
        self.delete(self.url(f"members/{self.user_id('bob@example.com')}/"))
        self.post(self.url("archive/"))
        texts = self.texts()
        self.assertTrue(any("was removed from the project" in t for t in texts))
        self.assertTrue(any("archived" in t for t in texts))


class DirectMessageTests(SlackTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.bob = self.user_id("bob@example.com")
        self.owner = self.user_id("owner@example.com")
        self.link_user("bob@example.com", "UBOB")
        self.link_user("owner@example.com", "UOWNER")

    def dms(self) -> list[tuple[str, str]]:
        return [(p["channel"], p["text"]) for p in self.hub.posts]

    def test_assignee_gets_a_dm_even_without_any_channel_mapping(self):
        self.create_task("Fix it", assignees=[self.bob])
        self.assertEqual([c for c, _ in self.dms()], ["UBOB"])
        self.assertIn("Task assigned to Bob", self.dms()[0][1])

    def test_assigning_yourself_does_not_notify_you(self):
        self.switch("bob@example.com")
        self.create_task("Mine", assignees=[self.bob])
        self.assertEqual(self.dms(), [])

    def test_unlinked_people_and_people_in_another_workspace_are_skipped(self):
        from integrations.models import LinkedAccount

        LinkedAccount.objects.filter(user_id=self.bob).delete()
        self.create_task("Unlinked", assignees=[self.bob])
        self.assertEqual(self.dms(), [])
        self.link_user("bob@example.com", "UBOB2", team="T-OTHER")
        self.create_task("Wrong workspace", assignees=[self.bob])
        self.assertEqual(self.dms(), [])

    def test_a_person_can_switch_dms_off_per_event(self):
        NotificationPreference.objects.create(
            user_id=self.bob, event_type="task_assigned", slack_dm=False
        )
        self.create_task("Quiet", assignees=[self.bob])
        self.assertEqual(self.dms(), [])
        task = self.create_task("Chatty", assignees=[self.bob])
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "hi"})
        self.assertEqual([c for c, _ in self.dms()], ["UBOB"])  # comment DM still on

    def test_the_email_flag_adds_an_email_without_removing_the_dm(self):
        NotificationPreference.objects.create(
            user_id=self.bob, event_type="task_assigned", email=True, slack_dm=True
        )
        mail.outbox.clear()
        self.create_task("Both ways", assignees=[self.bob])
        self.assertEqual(len(self.hub.posts), 1)
        mails = [m for m in mail.outbox if "Both ways" in m.subject]
        self.assertEqual([m.to for m in mails], [["bob@example.com"]])

    def test_comment_goes_to_assignees_and_creator_but_not_the_commenter(self):
        task = self.create_task("Shared", assignees=[self.bob])  # created by the owner
        self.hub.posts.clear()
        self.switch("bob@example.com")
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "from bob"})
        self.assertEqual([c for c, _ in self.dms()], ["UOWNER"])
        self.hub.posts.clear()
        self.switch("owner@example.com")
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "from owner"})
        self.assertEqual([c for c, _ in self.dms()], ["UBOB"])

    def test_due_dates_dm_the_assignees(self):
        from datetime import timedelta

        from django.utils import timezone

        from integrations.services import scan

        due = str(timezone.now().date() + timedelta(days=1))
        self.create_task("Soon", due_date=due, assignees=[self.bob])
        self.hub.posts.clear()
        scan.scan_due_dates()
        self.run_dispatch()
        self.assertEqual([c for c, _ in self.dms()], ["UBOB"])
        self.assertIn("due soon", self.dms()[0][1].lower())

    def test_join_requests_dm_the_owner_and_members_who_can_approve(self):
        self.put(
            self.url(f"members/{self.bob}/permissions/"),
            {"permissions": ["member.approve"]},
        )
        self.make_user("carl@example.com")
        self.hub.posts.clear()
        self.join(self.project, "carl@example.com")
        self.assertEqual(sorted(c for c, _ in self.dms()), ["UBOB", "UOWNER"])

    def test_people_who_left_the_project_stop_getting_dms(self):
        task = self.create_task("Bob's", assignees=[self.bob])
        self.delete(self.url(f"members/{self.bob}/"))
        self.hub.posts.clear()
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "hi"})
        self.assertNotIn("UBOB", [c for c, _ in self.dms()])
        self.assertIsNotNone(TEAM)


class FailureTests(SlackTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.map_channel("C1", ["task_created"])

    def post_task(self):
        with self.scheduled():
            self.create_task("Hello")
        return DeliveryAttempt.objects.get()

    def test_rate_limit_waits_without_using_an_attempt(self):
        self.hub.post_error = api_error(
            "ratelimited", status=429, headers={"Retry-After": "45"}
        )
        delivery = self.post_task()
        self.integration.refresh_from_db()
        self.assertEqual(
            (delivery.status, delivery.attempt, delivery.response_code),
            ("pending", 0, 429),
        )
        self.assertEqual(self.integration.consecutive_failures, 0)
        self.assertIsNotNone(self.integration.paused_until)

    def test_a_revoked_token_disconnects_the_integration_at_once(self):
        self.hub.post_error = api_error("token_revoked")
        delivery = self.post_task()
        self.integration.refresh_from_db()
        self.assertEqual(
            (self.integration.status, self.integration.encrypted_token),
            ("disconnected", ""),
        )
        self.assertEqual(delivery.error, "token_revoked")

    def test_channel_problems_are_failures_with_the_slack_reason(self):
        self.hub.post_error = api_error("channel_not_found")
        delivery = self.post_task()
        self.integration.refresh_from_db()
        self.assertEqual(
            (delivery.status, delivery.attempt, delivery.error),
            ("pending", 1, "channel_not_found"),
        )
        self.assertEqual(self.integration.status, "active")
        self.assertEqual(self.integration.consecutive_failures, 1)

    def test_a_failed_delivery_can_be_replayed(self):
        self.hub.post_error = api_error("is_archived")
        delivery = self.post_task()
        DeliveryAttempt.objects.update(status="failed", attempt=6)
        self.hub.post_error = None
        with self.scheduled():
            self.post(
                self.integrations_url(
                    f"{self.integration.pk}/deliveries/{delivery.pk}/replay/"
                )
            )
        delivery_service.run(str(delivery.pk))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, "success")

    def test_posts_survive_a_replay_with_the_same_content(self):
        self.hub.post_error = api_error("fatal_error")
        delivery = self.post_task()
        self.assertIn("Hello", delivery.payload["text"])
        self.assertEqual(delivery.payload["channel"], "C1")
        self.assertEqual(
            OutboxEvent.objects.filter(event_type="task_created").count(), 1
        )

    def test_disconnecting_revokes_the_token_at_slack(self):
        response = self.delete(self.integrations_url(f"{self.integration.pk}/"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.hub.revoked, 1)
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.encrypted_token, "")
