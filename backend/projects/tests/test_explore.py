from datetime import timedelta

from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from projects.models import JoinRequest, Project
from projects.tests.base import ProjectTestCase


class ExploreTestCase(ProjectTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.carl = self.make_user(
            "carl@example.com", first_name="Carl", display_name="Carl"
        )

    def listed(
        self, name: str, *, tags=None, owner="owner@example.com", key="AAA", **extra
    ) -> dict:
        self.switch(owner)
        project = self.create_project(name=name, task_key=key, tags=tags or [], **extra)
        response = self.patch(f"/api/projects/{project['id']}/", {"is_listed": True})
        assert response.status_code == 200, response.content
        return project

    def explore(self, user: str = "carl@example.com", **params) -> list[dict]:
        self.switch(user)
        query = "&".join(f"{k}={v}" for k, v in params.items())
        response = self.get("/api/explore/" + (f"?{query}" if query else ""))
        assert response.status_code == 200, response.content
        return response.json()["data"]["items"]

    def names(self, **params) -> list[str]:
        return [p["name"] for p in self.explore(**params)]


class ListingTests(ExploreTestCase):
    def test_only_listed_live_unarchived_projects_not_mine(self):
        listed = self.listed("Open Source")
        self.switch("owner@example.com")
        self.create_project(name="Private", task_key="PRV")  # never listed
        archived = self.listed("Archived", key="ARC")
        self.post(f"/api/projects/{archived['id']}/archive/")
        deleted = self.listed("Deleted", key="DEL")
        self.client.delete(
            f"/api/projects/{deleted['id']}/",
            {"password": "Correct-Horse-9"},
            format="json",
            **self._headers(),
        )
        self.assertEqual(self.names(), ["Open Source"])
        # Projects I belong to are not offered to me.
        self.assertEqual(self.names(user="owner@example.com"), [])
        self.assertIsNotNone(listed)

    def test_newest_listing_first_and_listed_at_follows_the_toggle(self):
        first = self.listed("First", key="FST")
        self.listed("Second", key="SND")
        self.assertEqual(self.names(), ["Second", "First"])
        self.switch("owner@example.com")
        self.patch(f"/api/projects/{first['id']}/", {"is_listed": False})
        self.assertIsNone(Project.objects.get(pk=first["id"]).listed_at)
        self.assertEqual(self.names(), ["Second"])
        self.switch("owner@example.com")
        self.patch(
            f"/api/projects/{first['id']}/", {"is_listed": True}
        )  # relisting moves it to the top
        self.assertEqual(self.names(), ["First", "Second"])

    def test_filters(self):
        self.listed(
            "Rocket",
            tags=["space", "science"],
            key="RKT",
            start_date="2026-03-01",
            end_date="2026-06-30",
            description="Moon base plans",
        )
        self.listed(
            "Garden",
            tags=["plants"],
            key="GRD",
            start_date="2026-09-01",
            end_date="2026-12-31",
        )
        self.assertEqual(self.names(q="moon"), ["Rocket"])
        self.assertEqual(self.names(q="GARD"), ["Garden"])
        self.assertEqual(self.names(tag="space"), ["Rocket"])
        self.assertEqual(
            sorted(self.names(tag="space&tag=plants")), ["Garden", "Rocket"]
        )  # any of
        self.assertEqual(self.names(tag="SPACE"), ["Rocket"])  # normalised
        self.assertEqual(self.names(starts_after="2026-08-01"), ["Garden"])
        self.assertEqual(self.names(ends_before="2026-07-01"), ["Rocket"])
        self.assertEqual(self.names(q="nothing matches"), [])
        self.assertEqual(self.get("/api/explore/?starts_after=soon").status_code, 400)
        self.assertEqual(self.get("/api/explore/?owner=1").status_code, 400)

    def test_what_a_stranger_sees_and_what_stays_hidden(self):
        project = self.listed("Open Source", tags=["oss"], description="Come help")
        item = self.explore()[0]
        self.assertEqual(
            set(item),
            {
                "id",
                "name",
                "description",
                "tags",
                "start_date",
                "end_date",
                "owner",
                "member_count",
                "is_demo",
                "listed_at",
                "my_request",
            },
        )
        self.assertEqual(item["owner"]["first_name"], "Ada")
        self.assertEqual(item["member_count"], 1)
        self.assertEqual(item["tags"], ["oss"])
        dump = str(item)
        self.assertNotIn(project["join_code"], dump)
        self.assertNotIn("@example.com", dump)

    def test_member_count_and_pagination(self):
        project = self.listed("Busy", key="BSY")
        self.add_member(project, "bob@example.com")
        self.listed("Quiet", key="QUT")
        items = self.explore()
        counts = {p["name"]: p["member_count"] for p in items}
        self.assertEqual(counts, {"Busy": 2, "Quiet": 1})
        self.switch("carl@example.com")
        body = self.get("/api/explore/?limit=1").json()
        self.assertEqual(len(body["data"]["items"]), 1)
        self.assertEqual(body["meta"]["count"], 2)

    def test_requires_login_and_only_the_owner_can_list(self):
        self.assertEqual(APIClient().get("/api/explore/").status_code, 401)
        project = self.create_project(name="Mine", task_key="MIN")
        self.add_member(project, "bob@example.com", preset="manager")
        self.switch("bob@example.com")
        self.assertEqual(
            self.patch(
                f"/api/projects/{project['id']}/", {"is_listed": True}
            ).status_code,
            403,
        )


class TagSuggestionTests(ExploreTestCase):
    def test_most_used_tags_among_listed_projects_only(self):
        self.listed("A", tags=["python", "web"], key="AAA")
        self.listed("B", tags=["python"], key="BBB")
        self.switch("owner@example.com")
        self.create_project(
            name="Hidden", task_key="HID", tags=["secret", "python"]
        )  # not listed
        self.switch("carl@example.com")
        tags = self.get("/api/explore/tags/").json()["data"]["items"]
        self.assertEqual(
            tags, [{"name": "python", "projects": 2}, {"name": "web", "projects": 1}]
        )
        self.assertEqual(
            self.get("/api/explore/tags/?q=PY").json()["data"]["items"],
            [{"name": "python", "projects": 2}],
        )
        self.assertEqual(
            self.get("/api/explore/tags/?q=secret").json()["data"]["items"], []
        )


class JoinFromExploreTests(ExploreTestCase):
    def test_request_without_a_code_notifies_the_owner_and_shows_pending(self):
        project = self.listed("Open Source")
        self.switch("carl@example.com")
        mail.outbox.clear()
        response = self.post(f"/api/explore/{project['id']}/join-request/")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["data"]["project"],
            {"name": "Open Source", "description": ""},
        )
        self.assertTrue(any(m.to == ["owner@example.com"] for m in mail.outbox))
        item = self.explore()[0]
        self.assertEqual(
            item["my_request"], {"state": "pending", "cooldown_until": None}
        )
        # The owner approves it like any other request.
        self.switch("owner@example.com")
        listing = self.get(f"/api/projects/{project['id']}/join-requests/").json()[
            "data"
        ]["items"]
        self.assertEqual(listing[0]["user"]["email"], "carl@example.com")
        self.assertEqual(
            self.post(
                f"/api/projects/{project['id']}/join-requests/{listing[0]['id']}/approve/"
            ).status_code,
            200,
        )

    def test_unlisted_archived_and_unknown_projects_are_404(self):
        self.switch("owner@example.com")
        hidden = self.create_project(name="Hidden", task_key="HID")
        listed = self.listed("Open", key="OPN")
        self.post(f"/api/projects/{listed['id']}/archive/")
        self.switch("carl@example.com")
        for project_id in (
            hidden["id"],
            listed["id"],
            "00000000-0000-0000-0000-000000000000",
        ):
            self.assertEqual(
                self.post(f"/api/explore/{project_id}/join-request/").status_code, 404
            )
        self.assertEqual(JoinRequest.objects.count(), 0)

    def test_same_rules_as_code_joins(self):
        project = self.listed("Open Source")
        self.switch("carl@example.com")
        self.post(f"/api/explore/{project['id']}/join-request/")
        again = self.post(f"/api/explore/{project['id']}/join-request/")
        self.assertEqual(again.json()["code"], "join_request_pending")
        # Already a member -> conflict.
        self.switch("owner@example.com")
        member = self.post(f"/api/explore/{project['id']}/join-request/")
        self.assertEqual(member.json()["code"], "already_member")
        # Rejected -> 24 hour cooldown, visible to the UI.
        listing = self.get(f"/api/projects/{project['id']}/join-requests/").json()[
            "data"
        ]["items"]
        self.post(
            f"/api/projects/{project['id']}/join-requests/{listing[0]['id']}/reject/"
        )
        self.switch("carl@example.com")
        blocked = self.post(f"/api/explore/{project['id']}/join-request/")
        self.assertEqual(blocked.json()["code"], "join_request_cooldown")
        state = self.explore()[0]["my_request"]
        self.assertEqual(state["state"], "cooldown")
        self.assertTrue(state["cooldown_until"])
        JoinRequest.objects.update(decided_at=timezone.now() - timedelta(hours=25))
        self.assertEqual(self.explore()[0]["my_request"]["state"], "none")
        self.assertEqual(
            self.post(f"/api/explore/{project['id']}/join-request/").status_code, 201
        )

    def test_the_open_request_cap_is_shared_with_code_joins(self):
        projects = [self.listed(f"P{i}", key=f"PA{chr(65 + i)}") for i in range(11)]
        self.switch("carl@example.com")
        for project in projects[:5]:
            self.assertEqual(
                self.post(f"/api/explore/{project['id']}/join-request/").status_code,
                201,
            )
        for project in projects[5:10]:
            self.assertEqual(
                self.post(
                    "/api/projects/join/", {"code": project["join_code"]}
                ).status_code,
                201,
            )
        capped = self.post(f"/api/explore/{projects[10]['id']}/join-request/")
        self.assertEqual(capped.json()["code"], "too_many_open_requests")

    def test_no_wrong_code_counter_and_own_rate_limit(self):
        from unittest import mock

        project = self.listed("Open Source")
        self.switch("carl@example.com")
        for _ in range(6):  # six wrong codes would lock code joins
            self.post("/api/projects/join/", {"code": "ZZZZZZ"})
        self.assertEqual(
            self.post(f"/api/explore/{project['id']}/join-request/").status_code, 201
        )
        with mock.patch.dict(
            "rest_framework.throttling.ScopedRateThrottle.THROTTLE_RATES",
            {"explore_join": "1/hour"},
        ):
            self.post(f"/api/explore/{project['id']}/join-request/")
            self.assertEqual(
                self.post(f"/api/explore/{project['id']}/join-request/").status_code,
                429,
            )


class MigrationTests(ExploreTestCase):
    def test_backfill_gives_listed_projects_a_listing_time(self):
        import importlib

        from django.apps import apps

        project = self.create_project(name="Old", task_key="OLD")
        Project.objects.filter(pk=project["id"]).update(is_listed=True, listed_at=None)
        migration = importlib.import_module(
            "projects.migrations.0005_backfill_listed_at"
        )
        migration.backfill(apps, None)
        row = Project.objects.get(pk=project["id"])
        self.assertEqual(row.listed_at, row.updated_at)
