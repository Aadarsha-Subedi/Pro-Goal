from datetime import timedelta
from unittest import mock

from django.core import mail
from django.utils import timezone

from integrations.constants.statuses import DeliveryStatus, IntegrationStatus
from integrations.models import DeliveryAttempt, OutboxEvent
from integrations.providers.base import DeliveryResult
from integrations.services import delivery as delivery_service
from integrations.services import dispatcher, integration_service
from integrations.tests.base import IntegrationTestCase

FAIL = DeliveryResult(ok=False, status_code=500, error="boom")


class DispatchTests(IntegrationTestCase):
    def test_a_change_reaches_the_provider(self):
        task = self.create_task("Ship it")
        delivery = DeliveryAttempt.objects.get(event_type="task_created")
        self.assertEqual(delivery.status, DeliveryStatus.SUCCESS)
        self.assertEqual((delivery.attempt, delivery.response_code), (1, 200))
        self.assertEqual(self.provider.delivered[-1]["title"], "Ship it")
        self.assertEqual(self.provider.delivered[-1]["task_number"], task["number"])
        self.assertTrue(
            OutboxEvent.objects.get(event_type="task_created").dispatched_at
        )

    def test_dispatch_is_idempotent(self):
        self.create_task()
        deliveries = DeliveryAttempt.objects.count()
        sent = len(self.provider.delivered)
        # Pretend the worker crashed before marking the event done: it is
        # dispatched again but no second delivery is created or sent.
        OutboxEvent.objects.filter(event_type="task_created").update(dispatched_at=None)
        self.run_dispatch()
        self.run_dispatch()
        self.assertEqual(DeliveryAttempt.objects.count(), deliveries)
        self.assertEqual(len(self.provider.delivered), sent)

    def test_provider_can_filter_events(self):
        self.provider.wanted = {"comment_added"}
        task = self.create_task()
        self.assertEqual(DeliveryAttempt.objects.count(), 0)
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "hi"})
        self.assertEqual(
            list(DeliveryAttempt.objects.values_list("event_type", flat=True)),
            ["comment_added"],
        )

    def test_a_provider_does_not_get_its_own_changes_back(self):
        from integrations.context import use_source

        with use_source("fake"):
            self.create_task("Made from the provider")
        self.assertEqual(DeliveryAttempt.objects.count(), 0)
        self.create_task("Made on the web")
        self.assertEqual(DeliveryAttempt.objects.count(), 1)

    def test_other_projects_integrations_are_not_used(self):
        other = self.create_project(name="Other", task_key="OTH")
        self.post(f"/api/projects/{other['id']}/tasks/", {"title": "elsewhere"})
        self.assertEqual(DeliveryAttempt.objects.count(), 0)

    def test_a_failing_subscriber_is_retried_then_given_up_on(self):
        from integrations.services import outbox

        calls = []

        def broken(event):
            calls.append(event.pk)
            raise RuntimeError("subscriber down")

        self.create_task()
        OutboxEvent.objects.all().delete()
        self.create_task("Again")
        OutboxEvent.objects.update(dispatched_at=None, dispatch_attempts=0)
        with mock.patch.object(outbox, "subscribers", [broken]):
            for _ in range(6):
                dispatcher.dispatch_batch()
        event = OutboxEvent.objects.get()
        self.assertEqual(len(calls), 5)
        self.assertEqual(event.dispatch_attempts, 5)
        self.assertIsNotNone(event.dispatched_at)
        self.assertIn("subscriber down", event.dispatch_error)


class RetryTests(IntegrationTestCase):
    def make_delivery(self) -> DeliveryAttempt:
        with self.scheduled():
            self.provider.results = []
            self.create_task()
        return DeliveryAttempt.objects.get()

    def test_retry_schedule_then_failed_and_replay(self):
        self.provider.results = [FAIL] * 6
        with self.scheduled() as enqueue:
            self.create_task()
            delivery = DeliveryAttempt.objects.get()
            expected = [
                timedelta(minutes=1),
                timedelta(minutes=5),
                timedelta(minutes=30),
                timedelta(hours=2),
                timedelta(hours=12),
            ]
            for number, wait in enumerate(expected, start=1):
                delivery.refresh_from_db()
                self.assertEqual(
                    (delivery.status, delivery.attempt),
                    (DeliveryStatus.PENDING, number),
                )
                self.assertAlmostEqual(
                    (delivery.next_retry_at - timezone.now()).total_seconds(),
                    wait.total_seconds(),
                    delta=5,
                )
                with self.captureOnCommitCallbacks(execute=True):
                    delivery_service.run(str(delivery.pk))
            delivery.refresh_from_db()
            self.assertEqual(
                (delivery.status, delivery.attempt), (DeliveryStatus.FAILED, 6)
            )
            self.assertIsNone(delivery.next_retry_at)
            self.assertEqual(delivery.error, "boom")
            scheduled_etas = [
                call.args[1] for call in enqueue.call_args_list if len(call.args) > 1
            ]
            self.assertEqual(len(scheduled_etas), 5)

        # A failed delivery can be replayed by hand and then succeeds.
        self.provider.results = []
        response = self.post(
            self.integrations_url(
                f"{self.integration.pk}/deliveries/{delivery.pk}/replay/"
            )
        )
        self.assertEqual(response.status_code, 200)
        delivery.refresh_from_db()
        self.assertEqual(
            (delivery.status, delivery.attempt), (DeliveryStatus.SUCCESS, 1)
        )

    def test_success_after_a_failure_resets_the_failure_counter(self):
        self.provider.results = [FAIL]
        with self.scheduled():
            self.create_task()
            self.integration.refresh_from_db()
            self.assertEqual(self.integration.consecutive_failures, 1)
            delivery = DeliveryAttempt.objects.get()
            delivery_service.run(str(delivery.pk))
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.consecutive_failures, 0)

    def test_rate_limit_pauses_without_using_an_attempt(self):
        self.provider.results = [
            DeliveryResult(ok=False, status_code=429, retry_after=120)
        ]
        with self.scheduled() as enqueue:
            self.create_task()
            delivery = DeliveryAttempt.objects.get()
            self.integration.refresh_from_db()
            self.assertEqual(
                (delivery.attempt, delivery.status), (0, DeliveryStatus.PENDING)
            )
            self.assertEqual(self.integration.consecutive_failures, 0)
            self.assertAlmostEqual(
                (self.integration.paused_until - timezone.now()).total_seconds(),
                120,
                delta=5,
            )
            self.assertEqual(delivery.response_code, 429)
            # While paused, another run does not even call the provider.
            sent = len(self.provider.delivered)
            delivery_service.run(str(delivery.pk))
            self.assertEqual(len(self.provider.delivered), sent)
            self.assertTrue(enqueue.called)
        self.integration.paused_until = timezone.now() - timedelta(seconds=1)
        self.integration.save()
        delivery_service.run(str(delivery.pk))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, DeliveryStatus.SUCCESS)

    def test_a_crashing_provider_counts_as_a_failure(self):
        with (
            mock.patch.object(
                type(self.provider), "deliver", side_effect=RuntimeError("kaboom")
            ),
            self.scheduled(),
        ):
            self.create_task()
        delivery = DeliveryAttempt.objects.get()
        self.assertEqual(
            (delivery.status, delivery.attempt), (DeliveryStatus.PENDING, 1)
        )
        self.assertIn("kaboom", delivery.error)


class HealthTests(IntegrationTestCase):
    def fail_ten_times(self):
        self.provider.results = [FAIL] * 20
        with self.scheduled():
            for index in range(10):
                self.create_task(f"t{index}")

    def test_ten_failures_need_attention_email_once_and_stop_sending(self):
        mail.outbox.clear()
        self.fail_ten_times()
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.status, IntegrationStatus.NEEDS_ATTENTION)
        self.assertEqual(self.integration.consecutive_failures, 10)
        health_mails = [m for m in mail.outbox if "needs attention" in m.subject]
        self.assertEqual(len(health_mails), 1)
        self.assertEqual(health_mails[0].to, ["owner@example.com"])
        self.assertIn("10 times", health_mails[0].body)

        # Nothing more is sent while it needs attention.
        sent = len(self.provider.delivered)
        deliveries = DeliveryAttempt.objects.count()
        self.create_task("after")
        self.assertEqual(len(self.provider.delivered), sent)
        self.assertEqual(DeliveryAttempt.objects.count(), deliveries)
        delivery = DeliveryAttempt.objects.filter(status="pending").first()
        delivery_service.run(str(delivery.pk))
        self.assertEqual(len(self.provider.delivered), sent)

    def test_reactivate_resets_and_sends_what_waited(self):
        self.fail_ten_times()
        self.provider.results = []
        waiting = DeliveryAttempt.objects.filter(status="pending").count()
        self.assertGreater(waiting, 0)
        with self.captureOnCommitCallbacks(execute=True):
            integration_service.reactivate(self.integration)
        self.integration.refresh_from_db()
        self.assertEqual(
            (
                self.integration.status,
                self.integration.consecutive_failures,
                self.integration.attention_notified,
            ),
            (IntegrationStatus.ACTIVE, 0, False),
        )
        self.assertEqual(DeliveryAttempt.objects.filter(status="pending").count(), 0)

    def test_owner_is_emailed_when_the_installer_is_gone(self):
        self.integration.installed_by = None
        self.integration.save()
        mail.outbox.clear()
        self.fail_ten_times()
        health_mails = [m for m in mail.outbox if "needs attention" in m.subject]
        self.assertEqual(health_mails[0].to, ["owner@example.com"])
