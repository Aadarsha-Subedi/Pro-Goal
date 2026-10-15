from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from projects.models import ActivityLog
from projects.tasks import purge_activity_log
from projects.tests.test_permissions import GrantTestCase


class ActivityFeedTests(GrantTestCase):
    def feed(self, **params) -> dict:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        response = self.get(self.url("activity/") + (f"?{query}" if query else ""))
        assert response.status_code == 200, response.content
        return response.json()

    def actions(self, **params) -> list[str]:
        return [e["action"] for e in self.feed(**params)["data"]["items"]]

    def setUp(self) -> None:
        super().setUp()
        self.grant("bob@example.com", preset="contributor")

    def test_owner_sees_everything_newest_first(self):
        self.post(self.url("tasks/"), {"title": "owner task"})
        self.switch("bob@example.com")
        self.post(self.url("tasks/"), {"title": "bob task"})
        self.switch("owner@example.com")
        body = self.feed()
        items = body["data"]["items"]
        self.assertEqual(body["meta"]["scope"], "all")
        titles = [
            e["changes"].get("title") for e in items if e["action"] == "task.created"
        ]
        self.assertEqual(titles, ["bob task", "owner task"])
        first_names = {e["actor"]["first_name"] for e in items}
        self.assertTrue({"Ada", "Bob"} <= first_names)
        stamps = [e["created_at"] for e in items]
        self.assertEqual(stamps, sorted(stamps, reverse=True))

    def test_members_without_activity_view_see_only_their_own_actions(self):
        self.post(self.url("tasks/"), {"title": "owner task"})
        self.switch("bob@example.com")
        self.post(self.url("tasks/"), {"title": "bob task"})
        body = self.feed()
        self.assertEqual(body["meta"]["scope"], "own")
        actors = {e["actor"]["id"] for e in body["data"]["items"]}
        self.assertEqual(actors, {self.uid("bob@example.com")})
        self.assertIn("task.created", self.actions())

    def test_the_actor_filter_cannot_be_used_to_peek_by_a_limited_member(self):
        self.post(self.url("tasks/"), {"title": "owner task"})
        self.switch("bob@example.com")
        items = self.feed(actor=self.uid("owner@example.com"))["data"]["items"]
        # The filter is ignored for limited members: still only Bob's entries.
        self.assertTrue(items)
        self.assertEqual(
            {e["actor"]["id"] for e in items}, {self.uid("bob@example.com")}
        )

    def test_granting_activity_view_widens_the_feed(self):
        self.post(self.url("tasks/"), {"title": "owner task"})
        self.grant("bob@example.com", ["activity.view"])
        self.switch("bob@example.com")
        body = self.feed()
        self.assertEqual(body["meta"]["scope"], "all")
        self.assertIn("task.created", self.actions())
        owner_only = self.feed(actor=self.uid("owner@example.com"))["data"]["items"]
        self.assertTrue(owner_only)
        self.assertTrue(all(e["actor"]["first_name"] == "Ada" for e in owner_only))

    def test_filters(self):
        task = self.post(self.url("tasks/"), {"title": "t"}).json()["data"]
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "hi"})
        self.assertEqual(self.actions(action="comment.created"), ["comment.created"])
        self.assertEqual(set(self.actions(entity_type="task")), {"task.created"})
        marker = (
            (timezone.now() + timedelta(hours=1)).isoformat().replace("+00:00", "Z")
        )
        self.assertEqual(self.feed(created_after=marker)["data"]["items"], [])
        self.assertTrue(self.feed(created_before=marker)["data"]["items"])
        self.assertEqual(
            self.get(self.url("activity/?actor=not-a-uuid")).status_code, 400
        )
        self.assertEqual(self.get(self.url("activity/?ip=1.2.3.4")).status_code, 400)

    def test_pagination(self):
        for index in range(5):
            self.post(self.url("tasks/"), {"title": f"t{index}"})
        body = self.feed(limit=2)
        self.assertEqual(len(body["data"]["items"]), 2)
        self.assertGreaterEqual(body["meta"]["count"], 5)

    def test_the_ip_is_never_returned_and_long_values_are_cut(self):
        long_text = "x" * 500
        task = self.post(self.url("tasks/"), {"title": "t"}).json()["data"]
        self.patch(self.url(f"tasks/{task['number']}/"), {"description": long_text})
        ActivityLog.objects.update(ip="203.0.113.9")
        response = self.get(self.url("activity/"))
        self.assertNotIn("203.0.113.9", response.content.decode())
        self.assertNotIn("ip", response.json()["data"]["items"][0])
        update = next(
            e for e in self.feed()["data"]["items"] if e["action"] == "task.updated"
        )
        shown = update["changes"]["description"]["to"]
        self.assertEqual(len(shown), 201)
        self.assertTrue(shown.endswith("…"))
        self.assertEqual(
            ActivityLog.objects.get(action="task.updated").changes["description"]["to"],
            long_text,
        )

    def test_deleted_actors_are_shown_as_deleted_user(self):
        self.switch("bob@example.com")
        self.post(self.url("tasks/"), {"title": "bob task"})
        self.switch("owner@example.com")
        self.delete(self.url(f"members/{self.uid('bob@example.com')}/"))
        User.objects.filter(email="bob@example.com").delete()
        entry = next(
            e for e in self.feed()["data"]["items"] if e["action"] == "task.created"
        )
        self.assertEqual(
            entry["actor"],
            {"id": None, "first_name": "Deleted user", "avatar_url": None},
        )

    def test_non_members_and_other_projects_are_isolated(self):
        self.make_user("eve@example.com")
        self.switch("eve@example.com")
        self.assertEqual(self.get(self.url("activity/")).status_code, 404)
        self.switch("owner@example.com")
        other = self.create_project(name="Other", task_key="OTH")
        entries = self.get(f"/api/projects/{other['id']}/activity/").json()["data"][
            "items"
        ]
        self.assertTrue(all(e["changes"].get("name") != "Apollo" for e in entries))

    def test_the_feed_stays_readable_when_archived(self):
        self.post(self.url("archive/"))
        self.assertIn("project.archived", self.actions())

    def test_requires_login(self):
        from rest_framework.test import APIClient

        self.assertEqual(APIClient().get(self.url("activity/")).status_code, 401)


class ActivityPurgeTests(GrantTestCase):
    def test_entries_older_than_a_year_are_purged(self):
        self.post(self.url("tasks/"), {"title": "recent"})
        old = ActivityLog.objects.first()
        ActivityLog.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=366)
        )
        borderline = ActivityLog.objects.exclude(pk=old.pk).first()
        ActivityLog.objects.filter(pk=borderline.pk).update(
            created_at=timezone.now() - timedelta(days=364)
        )
        remaining_before = ActivityLog.objects.count()
        self.assertEqual(purge_activity_log.delay().get(), 1)
        self.assertEqual(ActivityLog.objects.count(), remaining_before - 1)
        self.assertTrue(ActivityLog.objects.filter(pk=borderline.pk).exists())
