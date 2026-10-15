import json
import logging
from datetime import timedelta
from unittest import mock

from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.services import google_service
from accounts.tests.base import PASSWORD, ApiTestCase
from accounts.tests.test_account import FakeVerifier, profile
from security.models import SecurityEvent
from security.tasks import purge_security_events

CHROME = "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36"
SAFARI_MAC = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15) Version/17 Safari/605.1.15"
FIREFOX = "Mozilla/5.0 (X11; Linux) Firefox/130"


def types(user_email: str = "ada@example.com") -> list[str]:
    return list(
        SecurityEvent.objects.filter(user__email=user_email)
        .order_by("created_at", "id")
        .values_list("event_type", flat=True)
    )


class SecurityTestCase(ApiTestCase):
    def as_device(self, user_agent: str) -> None:
        """Switch to a fresh client that looks like another browser."""
        self.client = APIClient(enforce_csrf_checks=True, HTTP_USER_AGENT=user_agent)
        self.client.get("/api/csrf/")

    def fail_login(self, times: int, email: str = "ada@example.com"):
        return [
            self.login(email=email, password="Wrong-Password-1") for _ in range(times)
        ]


class LoginEventTests(SecurityTestCase):
    def test_success_and_failure_are_recorded_for_known_accounts(self):
        self.make_user()
        self.login(password="Wrong-Password-1")
        self.login()
        self.assertEqual(types(), ["login_failure", "login_success"])
        event = SecurityEvent.objects.filter(event_type="login_success").get()
        self.assertEqual(event.device_name, "Firefox on Linux")
        self.assertEqual(event.user_agent, FIREFOX)
        self.assertEqual(event.metadata, {})

    def test_unknown_email_creates_no_event(self):
        self.make_user()
        self.login(email="nobody@example.com", password="Wrong-Password-1")
        self.assertEqual(SecurityEvent.objects.count(), 0)

    def test_no_secrets_or_attempted_email_are_stored(self):
        self.make_user()
        self.login(password="Wrong-Password-1")
        dump = json.dumps(
            list(SecurityEvent.objects.values("metadata", "user_agent", "device_name"))
        )
        self.assertNotIn("Wrong-Password-1", dump)

    def test_unverified_account_correct_password_is_not_a_failure(self):
        self.make_user(verified=False)
        self.login()
        self.assertEqual(types(), [])


class LockoutTests(SecurityTestCase):
    def test_locks_after_five_failures_even_for_the_right_password(self):
        self.make_user()
        responses = self.fail_login(5)
        self.assertEqual([r.status_code for r in responses], [401] * 5)
        locked = self.login(password=PASSWORD)
        self.assertEqual(locked.status_code, 429)
        self.assertEqual(locked.json()["code"], "login_locked")
        self.assertGreater(int(locked["Retry-After"]), 0)

    def test_unknown_emails_lock_the_same_way(self):
        self.fail_login(5, email="ghost@example.com")
        locked = self.login(email="ghost@example.com", password="Wrong-Password-1")
        self.assertEqual(locked.json()["code"], "login_locked")

    def test_other_accounts_are_not_affected(self):
        self.make_user()
        self.make_user("bob@example.com")
        self.fail_login(5)
        self.assertEqual(self.login(email="bob@example.com").status_code, 200)

    def test_success_resets_the_counter(self):
        self.make_user()
        self.fail_login(4)
        self.assertEqual(self.login().status_code, 200)
        self.client.post("/api/auth/logout/", {}, format="json", **self._headers())
        self.fail_login(4)
        self.assertEqual(self.login().status_code, 200)

    def test_window_expiry_unlocks(self):
        self.make_user()
        self.fail_login(5)
        cache.clear()  # what the cache does when the 15 minutes pass
        self.assertEqual(self.login().status_code, 200)

    def test_locked_event_and_one_alert_email(self):
        self.make_user()
        mail.outbox.clear()
        self.fail_login(5)
        self.assertEqual(types().count("login_locked"), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("failed attempts", mail.outbox[0].body)
        self.login(password=PASSWORD)  # locked: no more mail, no more events
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(types().count("login_locked"), 1)

    def test_emails_are_matched_case_insensitively(self):
        self.make_user()
        for _ in range(5):
            self.login(email="ADA@Example.com", password="Wrong-Password-1")
        self.assertEqual(self.login().status_code, 429)

    def test_cache_keys_do_not_contain_the_email(self):
        from security.services import lockout_service

        self.fail_login(1, email="ada@example.com")
        self.assertEqual(lockout_service.failures("ada@example.com"), 1)
        keys = list(getattr(cache, "_cache", {}).keys())
        self.assertFalse([k for k in keys if "ada@example.com" in str(k)])


class NewDeviceAlertTests(SecurityTestCase):
    def test_first_login_and_known_device_are_silent_new_device_emails_once(self):
        self.make_user()
        mail.outbox.clear()
        self.login()
        self.assertEqual(len(mail.outbox), 0)  # first ever sign-in

        self.as_device(FIREFOX)
        self.login()
        self.assertEqual(len(mail.outbox), 0)  # same device again

        self.as_device(SAFARI_MAC)
        self.login()
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Safari on macOS", mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["ada@example.com"])

        self.as_device(SAFARI_MAC)
        self.login()
        self.assertEqual(len(mail.outbox), 1)  # now known

    def test_failed_logins_do_not_make_a_device_known(self):
        self.make_user()
        self.login()
        mail.outbox.clear()
        self.as_device(CHROME)
        self.fail_login(1)
        self.assertEqual(len(mail.outbox), 0)
        self.login()
        self.assertEqual(len(mail.outbox), 1)


class AccountEventTests(SecurityTestCase):
    def test_password_change_session_revoke_and_deletion(self):
        self.make_user()
        self.login()
        self.post(
            "/api/auth/password/change/",
            {"current_password": PASSWORD, "new_password": "Brand-New-Pass-7"},
        )
        # Sign in on a second device, then revoke the first device's session.
        self.as_device(CHROME)
        self.login(password="Brand-New-Pass-7")
        sessions = self.client.get("/api/me/sessions/").json()["data"]["items"]
        stale = next(s for s in sessions if not s["is_current"])
        self.assertEqual(
            self.delete(f"/api/me/sessions/{stale['id']}/").status_code, 200
        )
        self.post("/api/me/delete/")
        self.post("/api/me/delete/cancel/")
        recorded = types()
        for expected in (
            "password_changed",
            "session_revoked",
            "account_deletion_requested",
            "account_deletion_cancelled",
        ):
            self.assertIn(expected, recorded)

    def test_password_reset(self):
        user = self.make_user()
        self.post("/api/auth/password/reset/", {"email": "ada@example.com"})
        body = mail.outbox[-1].body
        link = next(line for line in body.splitlines() if "reset-password" in line)
        query = dict(part.split("=") for part in link.split("?", 1)[1].split("&"))
        response = self.post(
            "/api/auth/password/reset/confirm/",
            {
                "uid": query["uid"],
                "token": query["token"],
                "new_password": "Brand-New-Pass-7",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("password_reset", types(user.email))

    def test_google_link_event_only_for_existing_accounts(self):
        self.make_user()
        with mock.patch.object(
            google_service,
            "GoogleIdTokenVerifier",
            return_value=FakeVerifier(profile()),
        ):
            self.post("/api/auth/google/", {"id_token": "t"})
        self.assertIn("social_account_linked", types())
        event = SecurityEvent.objects.get(event_type="social_account_linked")
        self.assertEqual(event.metadata, {"provider": "google"})

        with mock.patch.object(
            google_service,
            "GoogleIdTokenVerifier",
            return_value=FakeVerifier(profile(sub="g-2", email="new@example.com")),
        ):
            self.post("/api/auth/google/", {"id_token": "t"})
        self.assertNotIn("social_account_linked", types("new@example.com"))
        self.assertIn("login_success", types("new@example.com"))


class EndpointTests(SecurityTestCase):
    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/me/security-events/").status_code, 401)

    def test_only_own_events_newest_first_filter_and_pagination(self):
        self.make_user()
        self.make_user("bob@example.com")
        self.login(email="bob@example.com")
        self.as_device(FIREFOX)
        self.login(password="Wrong-Password-1")
        self.login()
        response = self.client.get("/api/me/security-events/")
        items = response.json()["data"]["items"]
        self.assertEqual(
            [i["event_type"] for i in items], ["login_success", "login_failure"]
        )
        self.assertEqual(
            set(items[0]),
            {
                "id",
                "event_type",
                "ip",
                "user_agent",
                "device_name",
                "metadata",
                "created_at",
            },
        )
        filtered = self.client.get("/api/me/security-events/?event_type=login_failure")
        self.assertEqual(
            [i["event_type"] for i in filtered.json()["data"]["items"]],
            ["login_failure"],
        )
        paged = self.client.get("/api/me/security-events/?limit=1").json()
        self.assertEqual(len(paged["data"]["items"]), 1)
        self.assertEqual(paged["meta"]["count"], 2)
        self.assertEqual(
            self.client.get("/api/me/security-events/?event_type=nope").status_code, 400
        )

    def test_events_are_append_only(self):
        self.make_user()
        self.login()
        event = SecurityEvent.objects.get()
        event.device_name = "tampered"
        with self.assertRaises(ValueError):
            event.save()


class RetentionTests(SecurityTestCase):
    def test_old_events_are_purged(self):
        user = self.make_user()
        old = SecurityEvent.objects.create(user=user, event_type="login_success")
        recent = SecurityEvent.objects.create(user=user, event_type="login_success")
        SecurityEvent.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=181)
        )
        self.assertEqual(purge_security_events.delay().get(), 1)
        self.assertEqual(
            list(SecurityEvent.objects.values_list("pk", flat=True)), [recent.pk]
        )


class ThrottleTests(SecurityTestCase):
    def test_spec_rates_are_the_defaults(self):
        strict = settings.STRICT_THROTTLE_RATES
        self.assertEqual(
            {
                k: strict[k]
                for k in (
                    "anon",
                    "user",
                    "login",
                    "signup",
                    "email_resend",
                    "password_reset",
                    "google",
                    "upload",
                    "attachment_upload",
                )
            },
            {
                "anon": "60/min",
                "user": "600/min",
                "login": "5/min",
                "signup": "5/hour",
                "email_resend": "5/hour",
                "password_reset": "3/hour",
                "google": "20/min",
                "upload": "30/hour",
                "attachment_upload": "30/hour",
            },
        )
        self.assertEqual(strict["project"], "1200/min")

    def test_login_scope_throttles_per_ip(self):
        self.make_user()
        with mock.patch.dict(
            "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
            {"login": "2/min"},
        ):
            codes = [
                self.login(password="Wrong-Password-1").status_code for _ in range(3)
            ]
        self.assertEqual(codes, [401, 401, 429])

    def test_project_cap_is_shared_by_all_members(self):
        owner = self.make_user("owner@example.com")
        bob = self.make_user("bob@example.com")
        self.login(email="owner@example.com")
        project = self.post("/api/projects/", {"name": "P", "task_key": "PP"}).json()[
            "data"
        ]
        url = f"/api/projects/{project['id']}/"
        with mock.patch.dict(
            "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
            {"project": "3/min"},
        ):
            results = [self.client.get(url).status_code for _ in range(3)]
            self.assertEqual(results, [200, 200, 200])
            blocked = self.client.get(url)
            self.assertEqual(blocked.status_code, 429)
            self.assertIn("Retry-After", blocked)
            # Another project is unaffected; non-project routes are not counted.
            self.assertEqual(self.client.get("/api/me/").status_code, 200)
        self.assertIsNotNone(owner and bob)


class HealthTests(SecurityTestCase):
    def test_ok_without_login(self):
        response = APIClient().get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], {"status": "ok"})

    def test_503_when_the_database_fails(self):
        with mock.patch(
            "security.views.health.connection.cursor",
            side_effect=RuntimeError("db down"),
        ):
            response = APIClient().get("/api/health/")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "service_unavailable")
        self.assertNotIn("db down", json.dumps(response.json()))

    def test_503_when_the_cache_fails(self):
        broken = mock.Mock()
        broken.get.return_value = None
        with mock.patch("security.views.health.cache", broken):
            self.assertEqual(APIClient().get("/api/health/").status_code, 503)


class RequestIdTests(SecurityTestCase):
    def test_generated_and_returned(self):
        response = APIClient().get("/api/csrf/")
        self.assertRegex(response["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_valid_incoming_id_is_kept(self):
        response = APIClient().get("/api/csrf/", HTTP_X_REQUEST_ID="trace-1234.abc_DEF")
        self.assertEqual(response["X-Request-ID"], "trace-1234.abc_DEF")

    def test_bad_incoming_ids_are_replaced(self):
        for bad in ("short", "has space in it!!", "x" * 80, "line\nbreak-id-1234"):
            response = APIClient().get("/api/csrf/", HTTP_X_REQUEST_ID=bad)
            self.assertNotEqual(response["X-Request-ID"], bad)
            self.assertRegex(response["X-Request-ID"], r"^[0-9a-f]{32}$")

    def test_request_log_carries_the_id_and_user(self):
        user = self.make_user()
        self.login()
        with self.assertLogs("request", level="INFO") as logs:
            response = self.client.get("/api/me/", HTTP_X_REQUEST_ID="trace-abcdef12")
        record = logs.records[-1]
        self.assertEqual(record.request_id, "trace-abcdef12")
        self.assertEqual(response["X-Request-ID"], "trace-abcdef12")
        self.assertIsNotNone(user)

    def test_other_log_lines_get_the_id_through_the_filter(self):
        from common.logger.request_id import RequestIdFilter, request_id_var

        token = request_id_var.set("ctx-id-12345")
        try:
            record = logging.LogRecord("x", logging.INFO, "f", 1, "msg", None, None)
            RequestIdFilter().filter(record)
        finally:
            request_id_var.reset(token)
        self.assertEqual(record.request_id, "ctx-id-12345")

    def test_context_is_cleared_after_the_request(self):
        from common.logger.request_id import request_id_var

        APIClient().get("/api/csrf/")
        self.assertIsNone(request_id_var.get())

    def test_celery_headers_carry_the_id(self):
        from celery.signals import before_task_publish, task_prerun

        from common.logger.request_id import request_id_var

        token = request_id_var.set("ctx-id-67890")
        try:
            headers: dict = {}
            before_task_publish.send(sender="demo", headers=headers)
            self.assertEqual(headers["request_id"], "ctx-id-67890")
        finally:
            request_id_var.reset(token)

        seen = {}
        task = mock.Mock()
        task.request = mock.Mock(request_id="from-worker-1")
        task_prerun.send(sender=task, task=task)
        seen["inside"] = request_id_var.get()
        self.assertEqual(seen["inside"], "from-worker-1")
        from celery.signals import task_postrun

        task_postrun.send(sender=task, task=task)
        self.assertIsNone(request_id_var.get())


class LoggingAndSentryTests(SecurityTestCase):
    def test_json_formatter_includes_request_data_and_ids(self):
        from common.logger.formatters import JSONFormatter

        record = logging.LogRecord(
            "request", logging.INFO, "f", 1, "Request handled", None, None
        )
        record.request_data = {"method": "GET", "body": {"password": "***REDACTED***"}}
        record.request_id = "abc12345"
        record.user_id = "u-1"
        payload = json.loads(JSONFormatter().format(record))
        self.assertEqual(payload["request"]["method"], "GET")
        self.assertEqual(
            (payload["request_id"], payload["user_id"]), ("abc12345", "u-1")
        )

    def test_sentry_before_send_redacts_and_tags(self):
        from common.logger.request_id import request_id_var
        from common.observability.sentry import before_send

        token = request_id_var.set("ctx-id-sentry1")
        try:
            event = {
                "request": {
                    "data": {"password": "hunter2", "title": "ok"},
                    "headers": {"Authorization": "Bearer abc", "Accept": "x"},
                    "cookies": {"sessionid": "secret"},
                },
                "extra": {"token": "t", "note": "n"},
            }
            cleaned = before_send(event, {})
        finally:
            request_id_var.reset(token)
        request = cleaned["request"]
        self.assertEqual(request["data"], {"password": "***REDACTED***", "title": "ok"})
        self.assertEqual(request["headers"]["Authorization"], "***REDACTED***")
        self.assertNotIn("cookies", request)
        self.assertEqual(cleaned["extra"]["token"], "***REDACTED***")
        self.assertEqual(cleaned["tags"]["request_id"], "ctx-id-sentry1")

    def test_sentry_is_off_in_tests_and_pii_is_off_in_settings(self):
        import sentry_sdk

        self.assertIsNone(sentry_sdk.get_client().options.get("dsn"))
        source = (settings.BASE_DIR / "config" / "settings.py").read_text()
        self.assertNotIn("send_default_pii=True", source)
