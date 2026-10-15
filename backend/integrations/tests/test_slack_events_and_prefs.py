import time

from integrations.constants.statuses import IntegrationStatus
from integrations.models import Integration, LinkedAccount
from integrations.tests.slack_base import BOT_USER, TEAM, SlackTestCase


def envelope(event: dict, team: str = TEAM, event_id: str = "Ev1") -> dict:
    return {
        "type": "event_callback",
        "team_id": team,
        "event_id": event_id,
        "event_time": int(time.time()),
        "event": event,
    }


class EventsTests(SlackTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.other_project = self.create_project(name="Second", task_key="SEC")
        self.second = self.connect_slack(project_id=self.other_project["id"])
        self.elsewhere = self.create_project(name="Third", task_key="THR")
        self.third = self.connect_slack(project_id=self.elsewhere["id"], team="T-OTHER")
        self.link_user("bob@example.com", "UBOB")

    def statuses(self) -> dict[str, str]:
        return {str(i.project_id): i.status for i in Integration.objects.all()}

    def test_uninstall_disconnects_every_project_of_that_workspace_only(self):
        self.event(envelope({"type": "app_uninstalled"}))
        self.integration.refresh_from_db()
        self.second.refresh_from_db()
        self.third.refresh_from_db()
        self.assertEqual(self.integration.status, IntegrationStatus.DISCONNECTED)
        self.assertEqual(self.second.status, IntegrationStatus.DISCONNECTED)
        self.assertEqual(
            (self.integration.encrypted_token, self.integration.settings), ("", {})
        )
        self.assertEqual(self.third.status, IntegrationStatus.ACTIVE)
        self.assertEqual(self.hub.revoked, 0)  # already gone: no revoke call
        self.assertFalse(
            LinkedAccount.objects.filter(external_workspace_id=TEAM).exists()
        )

    def test_revoked_bot_token_disconnects_matching_integrations(self):
        self.event(envelope({"type": "tokens_revoked", "tokens": {"bot": [BOT_USER]}}))
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.status, IntegrationStatus.DISCONNECTED)
        self.third.refresh_from_db()
        self.assertEqual(self.third.status, IntegrationStatus.ACTIVE)

    def test_revoked_bot_token_of_another_bot_is_ignored(self):
        self.event(
            envelope({"type": "tokens_revoked", "tokens": {"bot": ["USOMEONEELSE"]}})
        )
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.status, IntegrationStatus.ACTIVE)

    def test_revoked_user_tokens_unlink_those_people(self):
        self.link_user("owner@example.com", "UOWNER")
        self.event(envelope({"type": "tokens_revoked", "tokens": {"oauth": ["UBOB"]}}))
        self.assertEqual(
            list(LinkedAccount.objects.values_list("external_user_id", flat=True)),
            ["UOWNER"],
        )

    def test_a_disconnected_project_stops_receiving_messages(self):
        self.map_channel("C1", ["task_created"])
        self.event(envelope({"type": "app_uninstalled"}))
        self.create_task("After uninstall")
        self.assertEqual(self.hub.posts, [])

    def test_unrelated_events_are_stored_and_ignored(self):
        self.event(envelope({"type": "channel_rename"}, event_id="Ev2"))
        self.assertEqual(set(self.statuses().values()), {"active"})


class PreferenceApiTests(SlackTestCase):
    URL = "/api/me/notification-preferences/"

    def effective(self, response) -> dict:
        return {
            i["event_type"]: (i["slack_dm"], i["email"])
            for i in response.json()["data"]["items"]
        }

    def test_defaults_cover_the_five_personal_events(self):
        values = self.effective(self.get(self.URL))
        self.assertEqual(
            values,
            {
                name: (True, False)
                for name in (
                    "task_assigned",
                    "task_due_soon",
                    "task_overdue",
                    "comment_added",
                    "join_request_created",
                )
            },
        )

    def test_partial_updates_keep_the_other_field_and_other_events(self):
        response = self.put(
            self.URL,
            {
                "preferences": {
                    "task_assigned": {"slack_dm": False},
                    "comment_added": {"email": True},
                }
            },
        )
        self.assertEqual(response.status_code, 200)
        values = self.effective(response)
        self.assertEqual(values["task_assigned"], (False, False))
        self.assertEqual(values["comment_added"], (True, True))
        self.assertEqual(values["task_overdue"], (True, False))
        again = self.put(self.URL, {"preferences": {"task_assigned": {"email": True}}})
        self.assertEqual(self.effective(again)["task_assigned"], (False, True))
        self.assertEqual(
            self.effective(self.get(self.URL))["task_assigned"], (False, True)
        )

    def test_each_person_has_their_own(self):
        self.put(self.URL, {"preferences": {"task_assigned": {"slack_dm": False}}})
        self.switch("bob@example.com")
        self.assertEqual(
            self.effective(self.get(self.URL))["task_assigned"], (True, False)
        )

    def test_validation(self):
        unknown = self.put(
            self.URL, {"preferences": {"task_created": {"slack_dm": False}}}
        )
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(unknown.json()["code"], "unknown_event")
        for body in (
            {},
            {"preferences": {}},
            {"preferences": {"task_assigned": {"sms": True}}},
            {"x": 1},
        ):
            self.assertEqual(self.put(self.URL, body).status_code, 400, body)

    def test_requires_login(self):
        from rest_framework.test import APIClient

        self.assertEqual(APIClient().get(self.URL).status_code, 401)
