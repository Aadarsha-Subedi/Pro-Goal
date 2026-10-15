from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from accounts.services import deletion_service
from accounts.services.reauth_service import Reauth
from common.exception.domain import ConflictException
from projects.constants.fields import JOIN_CODE_ALPHABET
from projects.models import ActivityLog, Membership, Project, Tag
from projects.services import project_service
from projects.tasks import purge_deleted_projects
from projects.tests.base import PASSWORD, FakeVerifier, ProjectTestCase


class CreateTests(ProjectTestCase):
    def test_create_makes_owner_and_code(self):
        data = self.create_project(tags=[" Backend ", "backend", "API"])
        self.assertEqual(data["role"], "owner")
        self.assertEqual(data["task_key"], "APL")
        self.assertEqual(data["tags"], ["api", "backend"])
        self.assertEqual(len(data["join_code"]), 6)
        self.assertTrue(set(data["join_code"]) <= set(JOIN_CODE_ALPHABET))
        self.assertEqual(Tag.objects.get(name="api").usage_count, 1)
        self.assertEqual(data["member_count"], 1)
        self.assertTrue(ActivityLog.objects.filter(action="project.created").exists())

    def test_validation(self):
        bad_key = self.post("/api/projects/", {"name": "x", "task_key": "A1"})
        self.assertEqual(bad_key.status_code, 400)
        dates = self.post(
            "/api/projects/",
            {
                "name": "x",
                "task_key": "AB",
                "start_date": "2026-02-01",
                "end_date": "2026-01-01",
            },
        )
        self.assertEqual(dates.status_code, 400)
        unknown = self.post(
            "/api/projects/", {"name": "x", "task_key": "AB", "owner": 1}
        )
        self.assertEqual(unknown.status_code, 400)

    def test_too_many_tags(self):
        response = self.post(
            "/api/projects/",
            {"name": "x", "task_key": "AB", "tags": [f"t{i}" for i in range(11)]},
        )
        self.assertEqual(response.status_code, 400)

    def test_list_only_own_projects(self):
        mine = self.create_project()
        self.switch("bob@example.com")
        self.assertEqual(self.get("/api/projects/").json()["data"]["items"], [])
        self.switch("owner@example.com")
        items = self.get("/api/projects/").json()["data"]["items"]
        self.assertEqual([i["id"] for i in items], [mine["id"]])

    def test_non_member_gets_404(self):
        project = self.create_project()
        self.switch("bob@example.com")
        response = self.get(f"/api/projects/{project['id']}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            self.patch(f"/api/projects/{project['id']}/", {"name": "x"}).status_code,
            404,
        )


class UpdateTests(ProjectTestCase):
    def test_owner_updates_and_logs(self):
        project = self.create_project(tags=["a"])
        response = self.patch(
            f"/api/projects/{project['id']}/",
            {"name": "Zeus", "tags": ["b"], "task_key": "zz", "description": "d"},
        )
        data = response.json()["data"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            (data["name"], data["task_key"], data["tags"]), ("Zeus", "ZZ", ["b"])
        )
        self.assertEqual(Tag.objects.get(name="a").usage_count, 0)
        self.assertEqual(Tag.objects.get(name="b").usage_count, 1)
        log = ActivityLog.objects.get(action="project.updated")
        self.assertEqual(log.changes["name"], {"from": "Apollo", "to": "Zeus"})

    def test_member_cannot_edit_and_sees_no_secrets(self):
        project = self.create_project()
        self.add_member(project)
        self.switch("bob@example.com")
        response = self.patch(
            f"/api/projects/{project['id']}/", {"name": "x", "description": "y"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "fields_forbidden")
        self.assertEqual(len(response.json()["errors"]), 2)
        detail = self.get(f"/api/projects/{project['id']}/").json()["data"]
        self.assertNotIn("join_code", detail)
        self.assertIn("task.create", detail["permissions"])
        self.assertNotIn("project.name.change", detail["permissions"])
        self.assertNotIn("status.create", detail["permissions"])

    def test_date_range_checked_against_stored_value(self):
        project = self.create_project(start_date="2026-05-01")
        response = self.patch(
            f"/api/projects/{project['id']}/", {"end_date": "2026-04-01"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_date_range")


class ArchiveDeleteTests(ProjectTestCase):
    def test_archive_blocks_writes_and_unarchive_restores(self):
        project = self.create_project()
        url = f"/api/projects/{project['id']}/"
        self.assertEqual(self.post(url + "archive/").status_code, 200)
        blocked = self.patch(url, {"name": "x"})
        self.assertEqual(blocked.status_code, 409)
        self.assertEqual(blocked.json()["code"], "project_archived")
        self.assertEqual(
            self.post(url + "unarchive/").json()["data"]["is_archived"], False
        )
        self.assertEqual(self.post(url + "unarchive/").status_code, 409)

    def test_member_cannot_archive(self):
        project = self.create_project()
        self.add_member(project)
        self.switch("bob@example.com")
        self.assertEqual(
            self.post(f"/api/projects/{project['id']}/archive/").status_code, 403
        )

    def test_delete_needs_reauth_then_restore(self):
        project = self.create_project()
        url = f"/api/projects/{project['id']}/"
        self.assertEqual(self.delete(url).status_code, 400)
        wrong = self.client.delete(
            url, {"password": "nope"}, format="json", **self._headers()
        )
        self.assertEqual(wrong.status_code, 403)
        self.assertEqual(wrong.json()["code"], "reauth_failed")
        ok = self.client.delete(
            url, {"password": PASSWORD}, format="json", **self._headers()
        )
        self.assertEqual(ok.status_code, 200)
        self.assertIsNotNone(ok.json()["data"]["deletion_scheduled_for"])
        # Owner still sees it; other writes are blocked; restore works.
        self.assertEqual(self.get(url).status_code, 200)
        self.assertEqual(
            self.patch(url, {"name": "x"}).json()["code"], "project_deleted"
        )
        self.assertEqual(self.post(url + "restore/").status_code, 200)
        self.assertFalse(self.project_row(project).is_deleted)

    def test_deleted_project_hidden_from_members_and_purged(self):
        project = self.create_project()
        self.add_member(project)
        self.switch("owner@example.com")
        url = f"/api/projects/{project['id']}/"
        self.client.delete(
            url, {"password": PASSWORD}, format="json", **self._headers()
        )
        self.switch("bob@example.com")
        self.assertEqual(self.get(url).status_code, 404)
        self.assertEqual(self.get("/api/projects/").json()["data"]["items"], [])

        Project.all_objects.filter(pk=project["id"]).update(
            deleted_at=timezone.now() - timedelta(days=8)
        )
        self.switch("owner@example.com")
        self.assertEqual(
            self.post(url + "restore/").json()["code"], "restore_window_over"
        )
        self.assertEqual(purge_deleted_projects.delay().get(), 1)
        self.assertFalse(Project.all_objects.filter(pk=project["id"]).exists())

    def test_regenerate_join_code(self):
        project = self.create_project()
        url = f"/api/projects/{project['id']}/join-code/regenerate/"
        self.assertEqual(self.post(url).status_code, 400)
        response = self.post(url, {"password": PASSWORD})
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.json()["data"]["join_code"], project["join_code"])


class ReauthTests(ProjectTestCase):
    def test_google_only_user_confirms_with_token(self):
        google = User.objects.create_user(
            email="g@example.com",
            password=None,
            first_name="G",
            last_name="U",
            display_name="G",
        )
        self.link_google(google, "g-1")
        membership = project_service.create(google, name="P", task_key="PP")
        good = FakeVerifier("g-1", "g@example.com")
        project_service.regenerate_join_code(
            membership, Reauth(id_token="tok"), verifier=good
        )
        for verifier in (
            FakeVerifier("other", "g@example.com"),
            FakeVerifier("g-1", "g@example.com", False),
        ):
            with self.assertRaises(Exception) as ctx:
                project_service.regenerate_join_code(
                    membership, Reauth(id_token="tok"), verifier=verifier
                )
            self.assertEqual(ctx.exception.error_code, "reauth_failed")
        with self.assertRaises(Exception) as ctx:
            project_service.regenerate_join_code(membership, Reauth(password="x"))
        self.assertEqual(ctx.exception.error_code, "reauth_failed")


class AccountDeletionTests(ProjectTestCase):
    def test_owning_a_project_blocks_account_deletion(self):
        project = self.create_project()
        with self.assertRaises(ConflictException):
            deletion_service.start_deletion(self.owner)
        self.assertEqual(self.post("/api/me/delete/").status_code, 409)
        # Still blocked while the project waits for its purge.
        self.client.delete(
            f"/api/projects/{project['id']}/",
            {"password": PASSWORD},
            format="json",
            **self._headers(),
        )
        self.assertEqual(self.post("/api/me/delete/").status_code, 409)
        self.assertEqual(Membership.objects.filter(user=self.owner).count(), 1)
