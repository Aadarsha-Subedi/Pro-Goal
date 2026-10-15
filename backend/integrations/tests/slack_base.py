import json
import time
from unittest import mock
from urllib.parse import urlencode

from cryptography.fernet import Fernet
from django.test import override_settings
from rest_framework.test import APIClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier

from accounts.models import User
from integrations.models import Integration
from integrations.providers import registry
from integrations.services import linking
from integrations.slack.provider import SlackProvider
from tracker.tests.base import TrackerTestCase

SECRET = "test-signing-secret"
TEAM = "T100"
BOT_USER = "UBOT"
TOKEN = "xoxb-test-bot-token"
HOOK = "https://hooks.slack.com/commands/T100/1/abc"


class FakeResponse(dict):
    """Enough of SlackResponse for the code under test."""

    def __init__(self, data=None, status_code=200, headers=None):
        super().__init__(data or {})
        self.status_code = status_code
        self.headers = headers or {}


def api_error(
    code: str, status: int = 200, headers: dict | None = None
) -> SlackApiError:
    return SlackApiError(
        code, FakeResponse({"ok": False, "error": code}, status, headers)
    )


class SlackHub:
    """Stands in for Slack: records calls and lets a test script the answers."""

    def __init__(self) -> None:
        self.posts: list[dict] = []
        self.replies: list[dict] = []
        self.revoked = 0
        self.post_error: SlackApiError | None = None
        self.channels = {
            "C1": {"id": "C1", "name": "dev", "is_private": False, "is_member": True},
            "C2": {
                "id": "C2",
                "name": "managers",
                "is_private": True,
                "is_member": True,
            },
            "C3": {
                "id": "C3",
                "name": "lonely",
                "is_private": False,
                "is_member": False,
            },
        }
        self.install_response = {
            "ok": True,
            "access_token": TOKEN,
            "bot_user_id": BOT_USER,
            "team": {"id": TEAM, "name": "Acme"},
        }
        self.token_response = {"ok": True, "access_token": "xoxp-user"}
        self.userinfo = {
            "ok": True,
            "sub": "UPERSON",
            "https://slack.com/team_id": TEAM,
            "email": "x@example.com",
        }
        self.oauth_error: SlackApiError | None = None
        self.list_error: SlackApiError | None = None

    def web(self, token: str | None = None):
        hub = self

        class Web:
            def chat_postMessage(self, **kwargs):
                if hub.post_error:
                    raise hub.post_error
                hub.posts.append({"token": token, **kwargs})
                return FakeResponse({"ok": True})

            def conversations_info(self, channel):
                if channel not in hub.channels:
                    raise api_error("channel_not_found")
                return FakeResponse({"ok": True, "channel": hub.channels[channel]})

            def conversations_list(self, **kwargs):
                if hub.list_error:
                    raise hub.list_error
                return FakeResponse(
                    {
                        "ok": True,
                        "channels": list(hub.channels.values()),
                        "response_metadata": {"next_cursor": ""},
                    }
                )

            def oauth_v2_access(self, **kwargs):
                if hub.oauth_error:
                    raise hub.oauth_error
                hub.last_oauth = kwargs
                return FakeResponse(hub.install_response)

            def openid_connect_token(self, **kwargs):
                if hub.oauth_error:
                    raise hub.oauth_error
                return FakeResponse(hub.token_response)

            def openid_connect_userInfo(self):
                return FakeResponse(hub.userinfo)

            def auth_revoke(self):
                hub.revoked += 1
                return FakeResponse({"ok": True, "revoked": True})

        return Web()

    def webhook(self, url: str):
        hub = self

        class Hook:
            def send(self, **kwargs):
                hub.replies.append({"url": url, **kwargs})

        return Hook()


def sign(body: str, timestamp: int | None = None, secret: str = SECRET) -> dict:
    stamp = str(timestamp if timestamp is not None else int(time.time()))
    signature = SignatureVerifier(secret).generate_signature(timestamp=stamp, body=body)
    return {
        "HTTP_X_SLACK_SIGNATURE": signature,
        "HTTP_X_SLACK_REQUEST_TIMESTAMP": stamp,
    }


class SlackTestCase(TrackerTestCase):
    """Owner + project + Bob (Contributor), Slack configured, the SDK replaced
    by a scripted hub, and the project connected to workspace T100."""

    def setUp(self) -> None:
        self.hub = SlackHub()
        for patcher in (
            override_settings(
                INTEGRATION_ENCRYPTION_KEYS=[Fernet.generate_key().decode()],
                SLACK_CLIENT_ID="cid",
                SLACK_CLIENT_SECRET="csecret",
                SLACK_SIGNING_SECRET=SECRET,
                PUBLIC_API_URL="https://api.test",
            ),
            mock.patch(
                "integrations.slack.client.web_client", side_effect=self.hub.web
            ),
            mock.patch(
                "integrations.slack.client.webhook_client", side_effect=self.hub.webhook
            ),
        ):
            patcher.enable() if hasattr(patcher, "enable") else patcher.start()
            self.addCleanup(
                patcher.disable if hasattr(patcher, "disable") else patcher.stop
            )
        super().setUp()
        registry.register(SlackProvider())
        self.addCleanup(registry.unregister, "slack")
        self.integration = self.connect_slack()

    def connect_slack(self, project_id=None, team: str = TEAM) -> Integration:
        integration = Integration.objects.create(
            project_id=project_id or self.pid,
            provider="slack",
            installed_by=User.objects.get(email="owner@example.com"),
            external_workspace_id=team,
            settings={"team_name": "Acme", "bot_user_id": BOT_USER},
        )
        integration.set_token(TOKEN)
        integration.save()
        return integration

    def link_user(self, email: str, slack_id: str, team: str = TEAM) -> None:
        linking.link(User.objects.get(email=email), "slack", slack_id, team)

    def map_channel(self, channel_id: str = "C1", events=None) -> dict:
        response = self.post(
            self.url("integrations/slack/mappings/"),
            {"channel_id": channel_id, "enabled_events": events or ["task_created"]},
        )
        assert response.status_code == 201, response.content
        return response.json()["data"]

    def slack_post(
        self, path: str, form: dict | None = None, raw: str | None = None, **headers
    ):
        """A call as Slack makes it: no session, signed with the secret."""
        body = raw if raw is not None else urlencode(form or {})
        content_type = (
            "application/json"
            if raw is not None
            else "application/x-www-form-urlencoded"
        )
        signed = headers or sign(body)
        return APIClient().post(path, data=body, content_type=content_type, **signed)

    def command(
        self,
        text: str,
        user: str = "UPERSON",
        team: str = TEAM,
        trigger: str = "trig-1",
        hook: str = HOOK,
    ):
        form = {
            "team_id": team,
            "user_id": user,
            "command": "/task",
            "text": text,
            "response_url": hook,
            "trigger_id": trigger,
        }
        with self.captureOnCommitCallbacks(execute=True):
            return self.slack_post("/api/integrations/slack/commands/", form)

    def event(self, payload: dict):
        with self.captureOnCommitCallbacks(execute=True):
            return self.slack_post(
                "/api/integrations/slack/events/", raw=json.dumps(payload)
            )

    @property
    def last_reply(self) -> str:
        return self.hub.replies[-1]["text"]

    def integrations_url(self, path: str) -> str:
        return self.url(f"integrations/{path}")

    def run_dispatch(self) -> int:
        from integrations.services import dispatcher

        with self.captureOnCommitCallbacks(execute=True):
            return dispatcher.dispatch_batch()

    def scheduled(self):
        """Capture scheduled retries instead of running them."""
        return mock.patch("integrations.services.delivery._enqueue")
