from io import StringIO

from cryptography.fernet import Fernet
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, override_settings

from accounts.models import User
from common.exception.domain import ServiceUnavailableException
from integrations import crypto
from integrations.context import use_source
from integrations.models import Integration, LinkedAccount, OutboxEvent
from integrations.services import linking
from integrations.tests.base import IntegrationTestCase
from projects.services import project_service


class CryptoTests(TestCase):
    def test_round_trip_and_ciphertext_differs(self):
        key = Fernet.generate_key().decode()
        with override_settings(INTEGRATION_ENCRYPTION_KEYS=[key]):
            secret = crypto.encrypt("xoxb-1")
            self.assertNotEqual(secret, "xoxb-1")
            self.assertNotIn("xoxb", secret)
            self.assertEqual(crypto.decrypt(secret), "xoxb-1")

    def test_missing_keys_is_a_clear_503(self):
        with (
            override_settings(INTEGRATION_ENCRYPTION_KEYS=[]),
            self.assertRaises(ServiceUnavailableException) as ctx,
        ):
            crypto.encrypt("x")
        self.assertEqual(ctx.exception.error_code, "integrations_not_configured")

    def test_an_invalid_key_is_a_clear_503_not_a_crash(self):
        for bad in ("not-a-key", "b'abc'", "too-short=", "x" * 44):
            with (
                override_settings(INTEGRATION_ENCRYPTION_KEYS=[bad]),
                self.assertRaises(ServiceUnavailableException) as ctx,
            ):
                crypto.encrypt("x")
            self.assertEqual(ctx.exception.error_code, "invalid_encryption_key")
            self.assertNotIn(bad, ctx.exception.message)

    def test_rotation_keeps_old_tokens_readable_and_command_reencrypts(self):
        old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        user = User.objects.create_user(
            "a@example.com",
            "pw-12345-Abc",
            first_name="A",
            last_name="B",
            display_name="A",
        )
        with override_settings(INTEGRATION_ENCRYPTION_KEYS=[old]):
            account = linking.link(user, "fake", "U1", "W1", token="tok-1")
        with override_settings(INTEGRATION_ENCRYPTION_KEYS=[new, old]):
            self.assertEqual(LinkedAccount.objects.get().get_token(), "tok-1")
            out = StringIO()
            call_command("rotate_integration_keys", stdout=out)
            self.assertIn("1 tokens", out.getvalue())
        # Now the old key can be dropped.
        with override_settings(INTEGRATION_ENCRYPTION_KEYS=[new]):
            self.assertEqual(LinkedAccount.objects.get().get_token(), "tok-1")
        self.assertIsNotNone(account)

    def test_tokens_are_not_stored_in_plain_text(self):
        with override_settings(
            INTEGRATION_ENCRYPTION_KEYS=[Fernet.generate_key().decode()]
        ):
            user = User.objects.create_user(
                "b@example.com",
                "pw-12345-Abc",
                first_name="A",
                last_name="B",
                display_name="A",
            )
            linking.link(user, "fake", "U1", "W1", token="xoxp-plain")
            self.assertNotIn("xoxp-plain", LinkedAccount.objects.get().encrypted_token)


class LinkingTests(IntegrationTestCase):
    def test_link_find_unlink_and_move(self):
        owner = User.objects.get(email="owner@example.com")
        bob = User.objects.get(email="bob@example.com")
        linking.link(owner, "fake", "U1", "W1")
        self.assertEqual(linking.find_user("fake", "W1", "U1"), owner)
        self.assertIsNone(linking.find_user("fake", "W2", "U1"))
        # Linking the same provider account to someone else moves it.
        linking.link(bob, "fake", "U1", "W1")
        self.assertEqual(linking.find_user("fake", "W1", "U1"), bob)
        self.assertFalse(LinkedAccount.objects.filter(user=owner).exists())
        self.assertEqual(linking.unlink(bob, "fake"), 1)
        self.assertIsNone(linking.find_user("fake", "W1", "U1"))

    def test_deleting_a_user_removes_their_links(self):
        bob = User.objects.get(email="bob@example.com")
        linking.link(bob, "fake", "U9", "W1")
        User.objects.filter(pk=bob.pk).delete()
        self.assertEqual(LinkedAccount.objects.count(), 0)


class EventMappingTests(IntegrationTestCase):
    def events(self, event_type: str | None = None):
        queryset = OutboxEvent.objects.filter(project_id=self.pid)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        return list(queryset.order_by("created_at", "id"))

    def test_task_created_and_updated(self):
        task = self.create_task("Plan release")
        created = self.events("task_created")[0]
        self.assertEqual(created.payload["title"], "Plan release")
        self.assertEqual(created.payload["task_number"], task["number"])
        self.assertEqual(created.source, "web")

        self.patch(
            self.url(f"tasks/{task['number']}/"),
            {"status": self.status_id("In progress")},
        )
        updated = self.events("task_updated")[0]
        self.assertEqual(
            updated.payload["changes"]["status"], {"from": "To do", "to": "In progress"}
        )
        self.assertEqual(updated.payload["title"], "Plan release")
        self.assertEqual(self.events("task_assigned"), [])

    def test_assignment_emits_one_event_per_newly_added_assignee(self):
        bob, owner = self.user_id("bob@example.com"), self.user_id("owner@example.com")
        task = self.create_task("Ship", assignees=[bob])
        url = self.url(f"tasks/{task['number']}/")
        self.patch(url, {"assignees": [bob, owner]})
        assigned = self.events("task_assigned")
        # Bob when the task was created, then only the newly added owner.
        self.assertEqual([e.payload["assignee_id"] for e in assigned], [bob, owner])
        self.patch(url, {"assignees": [owner]})  # only removing someone
        self.assertEqual(len(self.events("task_assigned")), 2)

    def test_comment_member_and_project_events_carry_no_secrets(self):
        task = self.create_task()
        self.post(
            self.url(f"tasks/{task['number']}/comments/"), {"body": "private text"}
        )
        comment = self.events("comment_added")[0]
        self.assertEqual(comment.payload["task_number"], task["number"])
        self.assertNotIn("private text", str(comment.payload))

        self.delete(self.url(f"members/{self.user_id('bob@example.com')}/"))
        removed = self.events("member_removed")[0]
        self.assertEqual(removed.payload["user_id"], self.user_id("bob@example.com"))
        self.assertFalse(removed.payload["left"])

        self.post(self.url("archive/"))
        self.assertEqual(len(self.events("project_archived")), 1)

    def test_join_events(self):
        self.make_user("carl@example.com")
        before = len(self.events("join_request_created"))  # Bob's, from setUp
        request = self.join(self.project, "carl@example.com")
        self.assertEqual(len(self.events("join_request_created")), before + 1)
        self.approve(self.project, request, "owner@example.com")
        joined = self.events("member_joined")
        self.assertEqual(
            joined[-1].payload["user_id"], self.user_id("carl@example.com")
        )
        self.switch("carl@example.com")
        self.post(self.url("leave/"))
        left = self.events("member_removed")[-1]
        self.assertTrue(left.payload["left"])

    def test_event_is_saved_with_the_change_and_rolled_back_with_it(self):
        from projects.models import Membership
        from tracker.services import task_service

        membership = Membership.objects.get(
            project_id=self.pid, user__email="owner@example.com"
        )
        before = OutboxEvent.objects.count()
        with self.assertRaises(RuntimeError), transaction.atomic():
            task_service.create(membership, {"title": "Doomed"})
            raise RuntimeError("something later fails")
        self.assertEqual(OutboxEvent.objects.count(), before)

    def test_unmapped_actions_emit_nothing(self):
        before = OutboxEvent.objects.count()
        self.patch(self.url(), {"name": "Renamed"})  # project.updated
        self.post(self.url("statuses/"), {"name": "QA", "category": "in_progress"})
        self.assertEqual(OutboxEvent.objects.count(), before)

    def test_source_tag_follows_the_context(self):
        with use_source("slack"):
            self.create_task("From slack")
        self.assertEqual(self.events("task_created")[-1].source, "slack")
        self.create_task("From web")
        self.assertEqual(self.events("task_created")[-1].source, "web")

    def test_projects_without_integrations_still_record_events(self):
        Integration.objects.all().delete()
        self.create_task()
        self.assertEqual(len(self.events("task_created")), 1)
        self.assertIsNotNone(project_service)
