from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APIClient

from integrations.constants.statuses import WebhookStatus
from integrations.models import InboundWebhook
from integrations.tests.base import IntegrationTestCase

URL = "/api/integrations/fake/webhook/"


class WebhookTests(IntegrationTestCase):
    def call(self, body: str = '{"x": 1}', **headers):
        client = APIClient()  # no session, no CSRF cookie: like a real provider
        return client.post(URL, data=body, content_type="application/json", **headers)

    def sign(self, delivery="d-1", **extra):
        headers = {"HTTP_X_FAKE_SIGNATURE": "ok", "HTTP_X_FAKE_DELIVERY": delivery}
        headers.update({f"HTTP_X_FAKE_{k.upper()}": v for k, v in extra.items()})
        return headers

    def test_bad_or_missing_signature_is_401_and_stores_nothing(self):
        self.assertEqual(self.call().status_code, 401)
        self.assertEqual(self.call(HTTP_X_FAKE_SIGNATURE="nope").status_code, 401)
        self.assertEqual(InboundWebhook.objects.count(), 0)
        self.assertEqual(self.call().json()["code"], "invalid_signature")

    def test_good_call_is_accepted_stored_and_processed(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.call('{"hello": "world"}', **self.sign())
        self.assertEqual(response.status_code, 202)
        webhook = InboundWebhook.objects.get()
        self.assertEqual((webhook.provider, webhook.delivery_id), ("fake", "d-1"))
        self.assertEqual(webhook.raw_payload, '{"hello": "world"}')
        self.assertEqual(webhook.status, WebhookStatus.PROCESSED)
        self.assertEqual(self.provider.handled, ["d-1"])

    def test_replayed_delivery_is_accepted_but_handled_once(self):
        for _ in range(3):
            with self.captureOnCommitCallbacks(execute=True):
                self.assertEqual(self.call(**self.sign()).status_code, 202)
        self.assertEqual(InboundWebhook.objects.count(), 1)
        self.assertEqual(self.provider.handled, ["d-1"])

    def test_older_event_for_the_same_item_is_ignored(self):
        now = timezone.now()
        newer, older = now.isoformat(), (now - timedelta(minutes=5)).isoformat()
        with self.captureOnCommitCallbacks(execute=True):
            self.call(**self.sign("d-new", timestamp=newer, item="task-1"))
            self.call(**self.sign("d-old", timestamp=older, item="task-1"))
            self.call(**self.sign("d-other", timestamp=older, item="task-2"))
        statuses = dict(InboundWebhook.objects.values_list("delivery_id", "status"))
        self.assertEqual(
            statuses,
            {"d-new": "processed", "d-old": "ignored", "d-other": "processed"},
        )
        self.assertEqual(self.provider.handled, ["d-new", "d-other"])

    def test_a_failing_handler_marks_the_call_failed(self):
        self.provider.handle_error = RuntimeError("cannot handle")
        with self.captureOnCommitCallbacks(execute=True):
            self.call(**self.sign())
        webhook = InboundWebhook.objects.get()
        self.assertEqual(webhook.status, WebhookStatus.FAILED)
        self.assertIn("cannot handle", webhook.error)

    def test_unknown_provider_is_404(self):
        response = APIClient().post(
            "/api/integrations/nope/webhook/",
            data="{}",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 404)

    def test_only_post_is_allowed(self):
        self.assertEqual(APIClient().get(URL).status_code, 405)

    def test_webhook_is_rate_limited_per_ip(self):
        from unittest import mock

        with mock.patch.dict(
            "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
            {"webhook": "2/min"},
        ):
            codes = [self.call(**self.sign(f"d-{i}")).status_code for i in range(3)]
        self.assertEqual(codes, [202, 202, 429])
