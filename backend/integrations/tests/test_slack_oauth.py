from unittest import mock
from urllib.parse import parse_qs, urlparse

from django.core import signing

from accounts.models import User
from integrations.constants.statuses import DeliveryStatus, IntegrationStatus
from integrations.models import (
    DeliveryAttempt,
    Integration,
    LinkedAccount,
    SlackChannelMapping,
)
from integrations.slack import constants, oauth
from integrations.tests.slack_base import TEAM, TOKEN, SlackTestCase, api_error


class InstallTests(SlackTestCase):
    def start_install(self) -> str:
        response = self.get(self.url("integrations/slack/install/"))
        assert response.status_code == 200, response.content
        return response.json()["data"]["url"]

    def callback(self, state: str, code: str = "code-1", **extra):
        query = {"state": state, "code": code, **extra}
        return self.client.get("/api/integrations/slack/install/callback/", query)

    def test_install_url_has_everything_slack_needs(self):
        url = urlparse(self.start_install())
        query = parse_qs(url.query)
        self.assertEqual(
            f"{url.scheme}://{url.netloc}{url.path}",
            "https://slack.com/oauth/v2/authorize",
        )
        self.assertEqual(query["client_id"], ["cid"])
        self.assertEqual(
            query["scope"], ["chat:write,commands,channels:read,groups:read"]
        )
        self.assertEqual(
            query["redirect_uri"],
            ["https://api.test/api/integrations/slack/install/callback/"],
        )
        self.assertTrue(query["state"][0])

    def test_install_needs_the_manage_permission(self):
        self.switch("bob@example.com")
        self.assertEqual(
            self.get(self.url("integrations/slack/install/")).status_code, 403
        )
        self.make_user("eve@example.com")
        self.switch("eve@example.com")
        self.assertEqual(
            self.get(self.url("integrations/slack/install/")).status_code, 404
        )

    def test_not_configured_is_a_clear_503(self):
        from django.test import override_settings

        with override_settings(SLACK_CLIENT_ID=""):
            response = self.get(self.url("integrations/slack/install/"))
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "slack_not_configured")

    def test_callback_stores_an_encrypted_token_and_redirects_to_the_frontend(self):
        Integration.objects.all().delete()
        state = parse_qs(urlparse(self.start_install()).query)["state"][0]
        response = self.callback(state)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            f"http://localhost:3000/projects/{self.pid}/integrations?slack=connected",
        )
        integration = Integration.objects.get()
        self.assertEqual(
            (
                integration.provider,
                integration.external_workspace_id,
                integration.status,
            ),
            ("slack", TEAM, "active"),
        )
        self.assertEqual(
            integration.settings, {"team_name": "Acme", "bot_user_id": "UBOT"}
        )
        self.assertEqual(integration.get_token(), TOKEN)
        self.assertNotIn(TOKEN, integration.encrypted_token)
        self.assertEqual(integration.installed_by.email, "owner@example.com")
        self.assertEqual(
            self.hub.last_oauth["redirect_uri"],
            "https://api.test/api/integrations/slack/install/callback/",
        )
        self.assertEqual(self.hub.last_oauth["code"], "code-1")

    def test_reconnect_updates_the_token_and_sends_what_waited(self):
        self.integration.status = IntegrationStatus.NEEDS_ATTENTION
        self.integration.consecutive_failures = 10
        self.integration.save()
        waiting = DeliveryAttempt.objects.create(
            integration=self.integration,
            event_type="task_created",
            payload={"channel": "C1", "text": "t", "blocks": []},
        )
        self.hub.install_response["access_token"] = "xoxb-new"
        state = parse_qs(urlparse(self.start_install()).query)["state"][0]
        with self.captureOnCommitCallbacks(execute=True):
            self.callback(state)
        self.integration.refresh_from_db()
        self.assertEqual(
            (self.integration.status, self.integration.consecutive_failures),
            ("active", 0),
        )
        self.assertEqual(self.integration.get_token(), "xoxb-new")
        self.assertEqual(Integration.objects.count(), 1)
        waiting.refresh_from_db()
        self.assertEqual(waiting.status, DeliveryStatus.SUCCESS)
        self.assertEqual(self.hub.posts[-1]["token"], "xoxb-new")

    def test_a_different_workspace_clears_the_old_channel_mappings(self):
        SlackChannelMapping.objects.create(
            integration=self.integration,
            channel_id="C1",
            channel_name="dev",
            enabled_events=["task_created"],
        )
        self.hub.install_response["team"] = {"id": "T999", "name": "Other"}
        state = parse_qs(urlparse(self.start_install()).query)["state"][0]
        self.callback(state)
        self.integration.refresh_from_db()
        self.assertEqual(self.integration.external_workspace_id, "T999")
        self.assertEqual(SlackChannelMapping.objects.count(), 0)

    def test_the_same_workspace_keeps_its_mappings(self):
        SlackChannelMapping.objects.create(
            integration=self.integration,
            channel_id="C1",
            channel_name="dev",
            enabled_events=[],
        )
        state = parse_qs(urlparse(self.start_install()).query)["state"][0]
        self.callback(state)
        self.assertEqual(SlackChannelMapping.objects.count(), 1)

    def test_one_workspace_can_serve_several_projects(self):
        other = self.create_project(name="Other", task_key="OTH")
        self.connect_slack(project_id=other["id"])
        self.assertEqual(
            Integration.objects.filter(external_workspace_id=TEAM).count(), 2
        )

    def test_bad_states_and_other_failures_redirect_with_a_reason(self):
        good = parse_qs(urlparse(self.start_install()).query)["state"][0]
        tampered = good[:-3] + ("abc" if not good.endswith("abc") else "xyz")
        cases = {
            "garbage": "invalid_oauth_state",
            tampered: "invalid_oauth_state",
            oauth.make_state(
                "link", User.objects.get(email="owner@example.com").pk, self.pid
            ): "invalid_oauth_state",
        }
        for state, reason in cases.items():
            response = self.callback(state)
            self.assertEqual(response.status_code, 302)
            self.assertIn("slack=error", response["Location"])
            self.assertIn(f"reason={reason}", response["Location"])
        self.assertEqual(self.hub.__dict__.get("last_oauth"), None)

    def test_expired_state(self):
        state = parse_qs(urlparse(self.start_install()).query)["state"][0]
        with mock.patch.object(constants, "STATE_MAX_AGE_SECONDS", -1):
            response = self.callback(state)
        self.assertIn("reason=invalid_oauth_state", response["Location"])

    def test_state_for_another_user_is_refused(self):
        state = parse_qs(urlparse(self.start_install()).query)["state"][0]
        self.switch("bob@example.com")
        response = self.callback(state)
        self.assertIn("reason=invalid_oauth_state", response["Location"])

    def test_not_signed_in_and_slack_denied(self):
        state = parse_qs(urlparse(self.start_install()).query)["state"][0]
        self.client.cookies.clear()
        self.assertIn("reason=not_signed_in", self.callback(state)["Location"])
        self.switch("owner@example.com")
        denied = self.client.get(
            "/api/integrations/slack/install/callback/",
            {"state": state, "error": "access_denied"},
        )
        self.assertIn("reason=access_denied", denied["Location"])

    def test_losing_the_manage_permission_before_the_callback_stops_the_install(self):
        Integration.objects.all().delete()
        state = parse_qs(urlparse(self.start_install()).query)["state"][0]
        self.switch("bob@example.com")  # not the user the state was made for
        self.assertIn("reason=invalid_oauth_state", self.callback(state)["Location"])
        self.assertEqual(Integration.objects.count(), 0)

    def test_slack_refusing_the_code_is_a_reason_not_a_crash(self):
        state = parse_qs(urlparse(self.start_install()).query)["state"][0]
        self.hub.oauth_error = api_error("invalid_code")
        response = self.callback(state)
        self.assertIn("reason=slack_error", response["Location"])
        self.assertIsNotNone(signing)


class LinkTests(SlackTestCase):
    def start_link(self) -> str:
        response = self.get("/api/me/integrations/slack/link/")
        assert response.status_code == 200, response.content
        return response.json()["data"]

    def callback(self, state: str, code: str = "code-1"):
        return self.client.get(
            "/api/integrations/slack/link/callback/", {"state": state, "code": code}
        )

    def test_link_url_and_callback_link_the_signed_in_person(self):
        data = self.start_link()
        url = urlparse(data["url"])
        query = parse_qs(url.query)
        self.assertEqual(
            f"{url.scheme}://{url.netloc}{url.path}",
            "https://slack.com/openid/connect/authorize",
        )
        self.assertEqual(query["scope"], ["openid"])
        self.assertEqual(data["linked_workspaces"], [])
        response = self.callback(query["state"][0])
        self.assertEqual(
            response["Location"],
            "http://localhost:3000/settings/integrations?slack=linked",
        )
        account = LinkedAccount.objects.get()
        self.assertEqual(
            (
                account.user.email,
                account.provider,
                account.external_user_id,
                account.external_workspace_id,
            ),
            ("owner@example.com", "slack", "UPERSON", TEAM),
        )
        self.assertEqual(self.start_link()["linked_workspaces"], [TEAM])

    def test_people_are_never_matched_by_email(self):
        # Slack says this account has Bob's email; it still links to the person signed in.
        self.hub.userinfo["email"] = "bob@example.com"
        state = parse_qs(urlparse(self.start_link()["url"]).query)["state"][0]
        self.callback(state)
        self.assertEqual(LinkedAccount.objects.get().user.email, "owner@example.com")

    def test_state_must_belong_to_the_signed_in_person(self):
        state = parse_qs(urlparse(self.start_link()["url"]).query)["state"][0]
        self.switch("bob@example.com")
        self.assertIn("reason=invalid_oauth_state", self.callback(state)["Location"])
        self.assertEqual(LinkedAccount.objects.count(), 0)
        install_state = oauth.make_state(
            "install", User.objects.get(email="bob@example.com").pk, self.pid
        )
        self.assertIn(
            "reason=invalid_oauth_state", self.callback(install_state)["Location"]
        )

    def test_relinking_moves_a_slack_account_and_unlink_removes_it(self):
        state = parse_qs(urlparse(self.start_link()["url"]).query)["state"][0]
        self.callback(state)
        self.switch("bob@example.com")
        state = parse_qs(urlparse(self.start_link()["url"]).query)["state"][0]
        self.callback(state)
        self.assertEqual(LinkedAccount.objects.get().user.email, "bob@example.com")
        self.assertEqual(
            self.delete("/api/me/integrations/slack/link/").status_code, 200
        )
        self.assertEqual(LinkedAccount.objects.count(), 0)

    def test_requires_login_and_a_configured_server(self):
        from django.test import override_settings
        from rest_framework.test import APIClient

        self.assertEqual(
            APIClient().get("/api/me/integrations/slack/link/").status_code, 401
        )
        with override_settings(SLACK_CLIENT_ID=""):
            self.assertEqual(
                self.get("/api/me/integrations/slack/link/").status_code, 503
            )
