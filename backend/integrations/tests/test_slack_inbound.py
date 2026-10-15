import json
import time
from unittest import mock

from rest_framework.test import APIClient

from integrations.models import InboundWebhook
from integrations.tests.slack_base import SlackTestCase, sign

COMMANDS = "/api/integrations/slack/commands/"
EVENTS = "/api/integrations/slack/events/"


class SignatureTests(SlackTestCase):
    def raw_command(self, headers: dict | None = None, body: str | None = None):
        body = (
            body
            or "team_id=T100&user_id=U1&text=&trigger_id=t1&response_url=https%3A%2F%2Fhooks.slack.com%2Fx"
        )
        return APIClient().post(
            COMMANDS,
            data=body,
            content_type="application/x-www-form-urlencoded",
            **(headers if headers is not None else sign(body)),
        )

    def test_valid_signature_is_acknowledged_with_an_empty_200(self):
        response = self.raw_command()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")
        self.assertEqual(InboundWebhook.objects.count(), 1)

    def test_wrong_secret_missing_headers_and_tampered_body_are_rejected(self):
        body = "team_id=T100&user_id=U1&text=&trigger_id=t1&response_url=x"
        cases = [
            sign(body, secret="another-secret"),
            {},
            sign(body) | {"HTTP_X_SLACK_SIGNATURE": "v0=deadbeef"},
        ]
        for headers in cases:
            response = APIClient().post(
                COMMANDS,
                data=body,
                content_type="application/x-www-form-urlencoded",
                **headers,
            )
            self.assertEqual(response.status_code, 401)
        tampered = APIClient().post(
            COMMANDS,
            data=body + "&extra=1",
            content_type="application/x-www-form-urlencoded",
            **sign(body),
        )
        self.assertEqual(tampered.status_code, 401)
        self.assertEqual(InboundWebhook.objects.count(), 0)

    def test_requests_older_than_five_minutes_are_rejected(self):
        body = "team_id=T100&user_id=U1&text=&trigger_id=t1&response_url=x"
        old = int(time.time()) - 6 * 60
        response = self.raw_command(sign(body, timestamp=old), body)
        self.assertEqual(response.status_code, 401)
        recent = self.raw_command(sign(body, timestamp=int(time.time()) - 60), body)
        self.assertEqual(recent.status_code, 200)

    def test_without_a_configured_secret_everything_is_refused(self):
        from django.test import override_settings

        body = "trigger_id=t1"
        with override_settings(SLACK_SIGNING_SECRET=""):
            response = self.raw_command(sign(body), body)
        self.assertEqual(response.status_code, 401)

    def test_a_repeated_trigger_is_accepted_but_stored_once(self):
        for _ in range(3):
            self.assertEqual(
                self.command("done PMS-1", trigger="same").status_code, 200
            )
        self.assertEqual(InboundWebhook.objects.count(), 1)


class EventsEndpointTests(SlackTestCase):
    def test_url_verification_echoes_the_challenge(self):
        body = json.dumps({"type": "url_verification", "challenge": "abc123"})
        response = self.slack_post(EVENTS, raw=body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"challenge": "abc123"})
        self.assertEqual(InboundWebhook.objects.count(), 0)

    def test_challenge_needs_a_valid_signature(self):
        body = json.dumps({"type": "url_verification", "challenge": "abc123"})
        response = APIClient().post(EVENTS, data=body, content_type="application/json")
        self.assertEqual(response.status_code, 401)

    def test_events_are_stored_once_by_event_id(self):
        payload = {
            "type": "event_callback",
            "team_id": TEAM_ID,
            "event_id": "Ev1",
            "event_time": int(time.time()),
            "event": {"type": "other"},
        }
        for _ in range(2):
            self.assertEqual(self.event(payload).status_code, 200)
        self.assertEqual(InboundWebhook.objects.filter(kind="events").count(), 1)
        self.assertEqual(InboundWebhook.objects.get().status, "processed")

    def test_other_methods_and_bad_json(self):
        self.assertEqual(APIClient().get(EVENTS).status_code, 405)
        response = self.slack_post(EVENTS, raw="not json")
        self.assertEqual(response.status_code, 400)
        self.assertIsNotNone(mock)


TEAM_ID = "T100"
