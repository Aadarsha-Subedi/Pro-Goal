from django.conf import settings
from django.test import SimpleTestCase

from common.logger.constants import SENSITIVE_KEYS
from common.logger.redaction import redact_sensitive_data
from integrations import tasks
from integrations.constants.events import EventType
from integrations.providers import registry
from integrations.testing import FakeProvider
from projects.constants import permissions as codes


class WiringTests(SimpleTestCase):
    def test_tasks_run_on_the_integrations_queue(self):
        for task in (
            tasks.dispatch_outbox,
            tasks.deliver,
            tasks.process_webhook,
            tasks.scan_due_dates,
            tasks.purge_old_records,
        ):
            self.assertEqual(task.queue, "integrations", task.name)

    def test_beat_schedule(self):
        beat = settings.CELERY_BEAT_SCHEDULE
        self.assertEqual(beat["dispatch-outbox"]["schedule"], 15.0)
        due = beat["scan-due-dates"]["schedule"]
        self.assertEqual((due.hour, due.minute), ({8}, {0}))
        self.assertIn("purge-integration-records", beat)

    def test_new_permission_codes_are_registered_and_in_the_manager_preset(self):
        for code in (
            codes.INTEGRATION_LOGS_VIEW,
            codes.INTEGRATION_SLACK_MANAGE,
            codes.ACTIVITY_VIEW,
        ):
            self.assertIn(code, codes.REGISTERED)
            self.assertIn(code, codes.PRESETS["manager"].codes)
            self.assertNotIn(code, codes.PRESETS["contributor"].codes)

    def test_fake_provider_manage_code_is_registered(self):
        self.assertIn(FakeProvider.manage_permission, codes.REGISTERED)

    def test_token_fields_are_redacted_in_logs(self):
        data = {
            "encrypted_token": "x",
            "bot_token": "y",
            "client_secret": "z",
            "signing_secret": "s",
            "ok": 1,
        }
        cleaned = redact_sensitive_data(data)
        self.assertEqual(cleaned["ok"], 1)
        self.assertTrue(all(cleaned[k] == "***REDACTED***" for k in data if k != "ok"))
        self.assertLessEqual(
            {"encrypted_token", "bot_token", "client_secret", "signing_secret"},
            SENSITIVE_KEYS,
        )

    def test_event_catalog_matches_the_spec(self):
        self.assertEqual(
            {e.value for e in EventType},
            {
                "task_created",
                "task_updated",
                "task_assigned",
                "task_due_soon",
                "task_overdue",
                "comment_added",
                "member_joined",
                "member_removed",
                "project_archived",
                "join_request_created",
            },
        )

    def test_the_fake_provider_is_not_registered_outside_tests(self):
        self.assertNotIn("fake", registry.codes())
