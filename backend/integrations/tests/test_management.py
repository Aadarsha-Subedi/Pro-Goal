from datetime import timedelta
from unittest import mock

from django.utils import timezone

from integrations.constants.statuses import IntegrationStatus
from integrations.models import (
    DeliveryAttempt,
    InboundWebhook,
    Integration,
    OutboxEvent,
)
from integrations.tasks import purge_old_records
from integrations.tests.base import IntegrationTestCase
from projects.models import Project
from projects.tasks import purge_deleted_projects


class ListAndLogTests(IntegrationTestCase):
    def test_owner_sees_health_but_never_the_token(self):
        response = self.get(self.integrations_url())
        item = response.json()["data"]["items"][0]
        self.assertEqual((item["provider"], item["status"]), ("fake", "active"))
        self.assertEqual(item["installed_by"]["first_name"], "Ada")
        self.assertNotIn(self.TOKEN, response.content.decode())
        self.assertNotIn("token", " ".join(item))

    def test_visibility_follows_the_permissions(self):
        self.switch("bob@example.com")  # Contributor: no logs.view, no manage
        self.assertEqual(self.get(self.integrations_url()).json()["data"]["items"], [])
        url = self.integrations_url(f"{self.integration.pk}/deliveries/")
        self.assertEqual(self.get(url).status_code, 403)

        self.switch("owner@example.com")
        self.put(
            self.url(f"members/{self.user_id('bob@example.com')}/permissions/"),
            {"permissions": ["integration.logs.view"]},
        )
        self.switch("bob@example.com")
        self.assertEqual(
            len(self.get(self.integrations_url()).json()["data"]["items"]), 1
        )
        self.assertEqual(self.get(url).status_code, 200)
        # Viewing logs is not managing.
        self.assertEqual(
            self.delete(self.integrations_url(f"{self.integration.pk}/")).status_code,
            403,
        )

    def test_non_members_get_404(self):
        self.make_user("eve@example.com")
        self.switch("eve@example.com")
        self.assertEqual(self.get(self.integrations_url()).status_code, 404)
        self.assertEqual(
            self.delete(self.integrations_url(f"{self.integration.pk}/")).status_code,
            404,
        )

    def test_delivery_log_filter_and_pagination(self):
        self.create_task("one")
        self.create_task("two")
        url = self.integrations_url(f"{self.integration.pk}/deliveries/")
        body = self.get(url).json()
        self.assertEqual(body["meta"]["count"], 2)
        self.assertEqual(self.get(url + "?status=failed").json()["data"]["items"], [])
        self.assertEqual(len(self.get(url + "?limit=1").json()["data"]["items"]), 1)
        self.assertEqual(self.get(url + "?status=nope").status_code, 400)
        item = body["data"]["items"][0]
        self.assertEqual(
            set(item),
            {
                "id",
                "direction",
                "event_type",
                "status",
                "attempt",
                "response_code",
                "next_retry_at",
                "error",
                "created_at",
                "updated_at",
            },
        )

    def test_replay_rules(self):
        self.create_task()
        delivery = DeliveryAttempt.objects.get()
        url = self.integrations_url(
            f"{self.integration.pk}/deliveries/{delivery.pk}/replay/"
        )
        self.assertEqual(
            self.post(url).json()["code"], "delivery_not_replayable"
        )  # it succeeded
        DeliveryAttempt.objects.update(status="failed")
        self.switch("bob@example.com")
        self.assertEqual(self.post(url).status_code, 403)
        self.switch("owner@example.com")
        self.integration.status = IntegrationStatus.NEEDS_ATTENTION
        self.integration.save()
        self.assertEqual(self.post(url).json()["code"], "integration_inactive")
        missing = self.integrations_url(
            f"{self.integration.pk}/deliveries/00000000-0000-0000-0000-000000000000/replay/"
        )
        self.assertEqual(self.post(missing).status_code, 404)


class DisconnectTests(IntegrationTestCase):
    def url_of(self):
        return self.integrations_url(f"{self.integration.pk}/")

    def test_disconnect_revokes_wipes_and_keeps_logs(self):
        self.create_task()
        response = self.delete(self.url_of())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["status"], "disconnected")
        self.assertEqual(self.provider.revoked, [self.TOKEN])
        self.integration.refresh_from_db()
        self.assertEqual(
            (self.integration.encrypted_token, self.integration.settings), ("", {})
        )
        self.assertEqual(DeliveryAttempt.objects.count(), 1)  # log history stays
        sent = len(self.provider.delivered)
        self.create_task("after")
        self.assertEqual(len(self.provider.delivered), sent)  # nothing more is sent

    def test_disconnect_succeeds_even_if_the_provider_is_down(self):
        self.provider.revoke_error = RuntimeError("provider down")
        self.assertEqual(self.delete(self.url_of()).status_code, 200)
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.status, "disconnected")
        self.assertEqual(self.integration.encrypted_token, "")

    def test_disconnect_twice_and_reconnect(self):
        self.delete(self.url_of())
        self.assertEqual(self.delete(self.url_of()).status_code, 200)
        self.assertEqual(self.provider.revoked, [self.TOKEN])  # revoked once
        self.connect()  # a new live integration is allowed after disconnecting
        self.assertEqual(Integration.objects.exclude(status="disconnected").count(), 1)

    def test_only_one_live_integration_per_provider_and_project(self):
        from django.db import IntegrityError, transaction

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.connect()

    def test_archived_project_blocks_disconnect(self):
        self.post(self.url("archive/"))
        self.assertEqual(self.delete(self.url_of()).json()["code"], "project_archived")

    def test_purging_a_project_revokes_tokens_first(self):
        Project.all_objects.filter(pk=self.pid).update(
            is_deleted=True, deleted_at=timezone.now() - timedelta(days=8)
        )
        purge_deleted_projects.delay().get()
        self.assertEqual(self.provider.revoked, [self.TOKEN])
        self.assertEqual(Integration.objects.count(), 0)


class RetentionTests(IntegrationTestCase):
    def test_old_records_are_purged_pending_ones_stay(self):
        self.create_task("a")
        self.create_task("b")
        old = timezone.now() - timedelta(days=31)
        deliveries = list(DeliveryAttempt.objects.all())
        DeliveryAttempt.objects.filter(pk=deliveries[0].pk).update(created_at=old)
        DeliveryAttempt.objects.filter(pk=deliveries[1].pk).update(
            created_at=old, status="pending"
        )
        OutboxEvent.objects.update(dispatched_at=old)
        InboundWebhook.objects.create(
            provider="fake", delivery_id="old", raw_payload="{}", status="processed"
        )
        InboundWebhook.objects.create(
            provider="fake", delivery_id="stuck", raw_payload="{}", status="received"
        )
        InboundWebhook.objects.update(received_at=old)
        result = purge_old_records.delay().get()
        self.assertEqual(result["webhooks"], 1)
        self.assertEqual(DeliveryAttempt.objects.count(), 1)
        self.assertEqual(DeliveryAttempt.objects.get().status, "pending")
        self.assertEqual(InboundWebhook.objects.get().delivery_id, "stuck")
        self.assertGreater(result["events"], 0)
        self.assertIsNotNone(mock)
