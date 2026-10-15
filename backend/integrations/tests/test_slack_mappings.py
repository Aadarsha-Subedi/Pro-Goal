from integrations.models import Integration, SlackChannelMapping
from integrations.tests.slack_base import SlackTestCase, api_error


class ChannelAndMappingTests(SlackTestCase):
    def mappings_url(self, suffix: str = "") -> str:
        return self.url(f"integrations/slack/mappings/{suffix}")

    def test_channels_are_listed_sorted_with_membership(self):
        channels = self.get(self.url("integrations/slack/channels/")).json()["data"][
            "items"
        ]
        self.assertEqual([c["name"] for c in channels], ["dev", "lonely", "managers"])
        self.assertEqual(
            next(c for c in channels if c["name"] == "lonely"),
            {"id": "C3", "name": "lonely", "is_private": False, "is_member": False},
        )

    def test_create_public_and_private_mappings(self):
        public = self.map_channel("C1", ["task_created", "comment_added"])
        self.assertEqual(
            (public["channel_name"], public["is_public"], public["warn_public"]),
            ("dev", True, True),
        )
        private = self.map_channel("C2", ["member_joined"])
        self.assertEqual((private["is_public"], private["warn_public"]), (False, False))
        listing = self.get(self.mappings_url()).json()["data"]["items"]
        self.assertEqual([m["channel_name"] for m in listing], ["dev", "managers"])

    def test_the_bot_must_have_been_invited(self):
        response = self.post(
            self.mappings_url(),
            {"channel_id": "C3", "enabled_events": ["task_created"]},
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "bot_not_in_channel")
        self.assertIn("Invite the bot", response.json()["message"])
        self.assertEqual(SlackChannelMapping.objects.count(), 0)

    def test_validation(self):
        unknown_event = self.post(
            self.mappings_url(),
            {"channel_id": "C1", "enabled_events": ["task_exploded"]},
        )
        self.assertEqual(unknown_event.json()["code"], "unknown_event")
        unknown_channel = self.post(
            self.mappings_url(), {"channel_id": "C9", "enabled_events": []}
        )
        self.assertEqual(unknown_channel.status_code, 502)
        self.assertEqual(unknown_channel.json()["code"], "slack_error")
        extra = self.post(
            self.mappings_url(), {"channel_id": "C1", "enabled_events": [], "x": 1}
        )
        self.assertEqual(extra.status_code, 400)

    def test_duplicates_are_refused_and_events_deduplicated(self):
        self.map_channel("C1", ["task_created", "task_created"])
        self.assertEqual(
            SlackChannelMapping.objects.get().enabled_events, ["task_created"]
        )
        again = self.post(
            self.mappings_url(), {"channel_id": "C1", "enabled_events": []}
        )
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.json()["code"], "duplicate_mapping")

    def test_update_and_delete(self):
        mapping = self.map_channel("C1", ["task_created"])
        url = self.mappings_url(f"{mapping['id']}/")
        changed = self.patch(url, {"enabled_events": ["comment_added", "task_overdue"]})
        self.assertEqual(
            changed.json()["data"]["enabled_events"], ["comment_added", "task_overdue"]
        )
        self.assertEqual(self.patch(url, {"enabled_events": ["nope"]}).status_code, 400)
        self.assertEqual(self.delete(url).status_code, 200)
        self.assertEqual(self.delete(url).status_code, 404)

    def test_everything_needs_the_manage_permission_and_membership(self):
        mapping = self.map_channel("C1")
        self.switch("bob@example.com")  # Contributor: no integration.slack.manage
        for response in (
            self.get(self.url("integrations/slack/channels/")),
            self.get(self.mappings_url()),
            self.post(self.mappings_url(), {"channel_id": "C1", "enabled_events": []}),
            self.patch(self.mappings_url(f"{mapping['id']}/"), {"enabled_events": []}),
            self.delete(self.mappings_url(f"{mapping['id']}/")),
        ):
            self.assertEqual(response.status_code, 403)
        self.switch("owner@example.com")
        self.put(
            self.url(f"members/{self.user_id('bob@example.com')}/permissions/"),
            {"permissions": ["integration.slack.manage"]},
        )
        self.switch("bob@example.com")
        self.assertEqual(self.get(self.mappings_url()).status_code, 200)
        self.make_user("eve@example.com")
        self.switch("eve@example.com")
        self.assertEqual(self.get(self.mappings_url()).status_code, 404)

    def test_other_projects_mappings_are_invisible(self):
        other = self.create_project(name="Other", task_key="OTH")
        self.connect_slack(project_id=other["id"])
        self.map_channel("C1")
        url = f"/api/projects/{other['id']}/integrations/slack/mappings/"
        self.assertEqual(self.get(url).json()["data"]["items"], [])

    def test_a_project_without_slack_gets_404(self):
        Integration.objects.all().delete()
        self.assertEqual(
            self.get(self.mappings_url()).json()["code"], "slack_not_connected"
        )

    def test_archived_project_blocks_changes_but_not_reading(self):
        mapping = self.map_channel("C1")
        self.post(self.url("archive/"))
        self.assertEqual(self.get(self.mappings_url()).status_code, 200)
        blocked = self.patch(
            self.mappings_url(f"{mapping['id']}/"), {"enabled_events": []}
        )
        self.assertEqual(blocked.json()["code"], "project_archived")

    def test_a_revoked_token_found_while_listing_disconnects_the_integration(self):
        self.hub.list_error = api_error("token_revoked")
        response = self.get(self.url("integrations/slack/channels/"))
        self.assertEqual(response.status_code, 502)
        self.integration.refresh_from_db()
        self.assertEqual(
            (self.integration.status, self.integration.encrypted_token),
            ("disconnected", ""),
        )
