from io import StringIO

from allauth.account.models import EmailAddress
from django.core import mail
from django.core.management import call_command

from accounts.models import User
from accounts.services.tokens import make_verification_token
from accounts.tests.base import PASSWORD
from projects.models import Membership, Project
from projects.services import demo_service
from projects.tests.base import ProjectTestCase
from tracker.models import Comment, Note, Priority, Status, Task, TaskCounter


class DemoTestCase(ProjectTestCase):
    def setUp(self) -> None:
        super().setUp()
        call_command("seed_demo_projects", stdout=StringIO())
        self.demo = Project.objects.filter(demo_key__isnull=False).order_by("name")[0]

    def join_demo(self, email: str = "bob@example.com") -> dict:
        self.switch(email)
        response = self.post(f"/api/explore/{self.demo.pk}/join-request/")
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()["data"]


class SeedTests(DemoTestCase):
    def test_seed_creates_system_owned_listed_projects(self):
        projects = Project.objects.filter(demo_key__isnull=False)
        self.assertEqual(projects.count(), 3)
        system = User.objects.get(is_system=True)
        for project in projects:
            self.assertEqual(project.owner, system)
            self.assertTrue(project.is_listed)
            self.assertTrue(Task.objects.filter(project=project).exists())
            self.assertFalse(
                Task.objects.filter(project=project, due_date__isnull=False).exists()
            )
        self.assertFalse(system.has_usable_password())

    def test_seed_is_idempotent_and_refresh_rebuilds(self):
        before = Task.objects.filter(project=self.demo).count()
        call_command("seed_demo_projects", stdout=StringIO())
        self.assertEqual(Project.objects.filter(demo_key__isnull=False).count(), 3)
        self.assertEqual(Task.objects.filter(project=self.demo).count(), before)
        Task.objects.filter(project=self.demo).first().delete()
        call_command("seed_demo_projects", refresh=True, stdout=StringIO())
        self.assertEqual(Task.objects.filter(project=self.demo).count(), before)
        counter = TaskCounter.objects.get(project=self.demo)
        self.assertEqual(counter.next_number, before + 1)
        self.assertEqual(User.objects.filter(is_system=True).count(), 1)

    def test_seeded_parents_resolve(self):
        child = Task.objects.filter(project=self.demo, parent__isnull=False).first()
        self.assertIsNotNone(child)
        self.assertEqual(child.parent.project_id, self.demo.pk)


class SystemUserTests(DemoTestCase):
    def test_system_user_cannot_log_in_or_reset_password(self):
        response = self.login(demo_service.SYSTEM_USER_EMAIL, PASSWORD)
        self.assertEqual(response.status_code, 401)
        mail.outbox.clear()
        response = self.post(
            "/api/auth/password/reset/", {"email": demo_service.SYSTEM_USER_EMAIL}
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_system_user_is_not_purged(self):
        system = User.objects.get(is_system=True)
        system.is_deleted = True
        system.deleted_at = system.created_at
        system.save()
        from accounts.services import deletion_service

        deletion_service.purge_expired_accounts()
        self.assertTrue(User.objects.filter(is_system=True).exists())


class AutoJoinTests(DemoTestCase):
    def test_verifying_email_joins_every_demo_as_a_viewer(self):
        user = self.make_user("new@example.com", verified=False)
        address = EmailAddress.objects.get(user=user)
        response = self.post(
            "/api/auth/verify-email/", {"token": make_verification_token(address.pk)}
        )
        self.assertEqual(response.status_code, 200, response.content)
        memberships = Membership.objects.filter(user=user)
        self.assertEqual(memberships.count(), 3)
        self.assertFalse(any(m.is_owner for m in memberships))
        self.assertFalse(any(m.grants.exists() for m in memberships))

    def test_leaving_is_not_undone_by_a_later_login(self):
        user = self.make_user("new@example.com", verified=False)
        address = EmailAddress.objects.get(user=user)
        self.post(
            "/api/auth/verify-email/", {"token": make_verification_token(address.pk)}
        )
        self.switch("new@example.com")
        response = self.post(f"/api/projects/{self.demo.pk}/leave/")
        self.assertEqual(response.status_code, 200, response.content)
        self.switch("new@example.com")
        self.assertFalse(
            Membership.objects.filter(user=user, project=self.demo).exists()
        )

    def test_join_all_is_idempotent(self):
        demo_service.join_all_demo_projects(self.bob)
        demo_service.join_all_demo_projects(self.bob)
        self.assertEqual(Membership.objects.filter(user=self.bob).count(), 3)


class OpenJoinTests(DemoTestCase):
    def test_explore_join_is_immediate_for_demo_projects(self):
        data = self.join_demo()
        self.assertEqual(data["status"], "joined")
        membership = Membership.objects.get(user=self.bob, project=self.demo)
        self.assertFalse(membership.is_owner)
        self.assertEqual(len(mail.outbox), 0)

    def test_demo_projects_cannot_be_joined_by_code(self):
        self.switch("bob@example.com")
        response = self.post("/api/projects/join/", {"code": self.demo.join_code})
        self.assertEqual(response.status_code, 404)

    def test_explore_marks_demo_projects(self):
        self.switch("bob@example.com")
        items = self.get("/api/explore/").json()["data"]["items"]
        self.assertTrue(all(item["is_demo"] for item in items))

    def test_member_list_shows_only_owner_and_caller(self):
        self.join_demo()
        self.join_demo("owner@example.com")
        self.switch("bob@example.com")
        members = self.get(f"/api/projects/{self.demo.pk}/members/").json()["data"][
            "items"
        ]
        self.assertEqual(len(members), 2)
        self.assertEqual(sum(m["is_owner"] for m in members), 1)


class GuardTests(DemoTestCase):
    def test_viewers_cannot_edit_archive_or_delete_a_demo_project(self):
        self.join_demo()
        base = f"/api/projects/{self.demo.pk}/"
        for response in (
            self.patch(base, {"name": "Hacked"}),
            self.post(base + "archive/"),
            self.client.delete(
                base, {"password": PASSWORD}, format="json", **self._headers()
            ),
        ):
            self.assertIn(response.status_code, (403, 409), response.content)
        self.demo.refresh_from_db()
        self.assertTrue(self.demo.name.startswith("Demo:"))
        self.assertIsNone(self.demo.archived_at)
        self.assertFalse(self.demo.is_deleted)

    def test_even_the_system_owner_is_blocked_at_the_service_layer(self):
        from common.exception.domain import ConflictException
        from projects.services import project_service

        owner = Membership.objects.get(project=self.demo, is_owner=True)
        for call in (
            lambda: project_service.update(owner, {"name": "x"}),
            lambda: project_service.archive(owner),
            lambda: project_service.unarchive(owner),
            lambda: project_service.restore(owner),
        ):
            with self.assertRaises(ConflictException) as caught:
                call()
            self.assertEqual(caught.exception.error_code, "demo_project_locked")

    def test_viewer_cannot_write_tasks(self):
        self.join_demo()
        status = Status.objects.filter(project=self.demo).first()
        priority = Priority.objects.filter(project=self.demo).first()
        response = self.post(
            f"/api/projects/{self.demo.pk}/tasks/",
            {"title": "Mine", "status": str(status.pk), "priority": str(priority.pk)},
        )
        self.assertEqual(response.status_code, 403)

    def test_demo_projects_survive_the_purge_job(self):
        from projects.services import project_service

        Project.all_objects.filter(pk=self.demo.pk).update(
            is_deleted=True, deleted_at=self.demo.created_at
        )
        project_service.purge_deleted_projects()
        self.assertTrue(Project.all_objects.filter(pk=self.demo.pk).exists())


class CopyTests(DemoTestCase):
    def copy(self, **body):
        return self.post(f"/api/projects/{self.demo.pk}/copy/", body)

    def test_copy_clones_content_into_a_project_the_user_owns(self):
        self.join_demo()
        response = self.copy()
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()["data"]
        self.assertEqual(data["role"], "owner")
        self.assertFalse(data["is_demo"])
        self.assertFalse(data["is_listed"])
        copy = Project.objects.get(pk=data["id"])
        self.assertEqual(copy.owner, self.bob)
        self.assertEqual(copy.copied_from, self.demo)
        self.assertNotEqual(copy.join_code, self.demo.join_code)
        source_tasks = Task.objects.filter(project=self.demo).order_by("number")
        copy_tasks = Task.objects.filter(project=copy).order_by("number")
        self.assertEqual([t.title for t in copy_tasks], [t.title for t in source_tasks])
        self.assertEqual(
            [t.parent.number if t.parent else None for t in copy_tasks],
            [t.parent.number if t.parent else None for t in source_tasks],
        )
        self.assertEqual(
            [t.status.name for t in copy_tasks], [t.status.name for t in source_tasks]
        )
        self.assertTrue(all(t.status.project_id == copy.pk for t in copy_tasks))
        self.assertEqual(
            Status.objects.filter(project=copy).count(),
            Status.objects.filter(project=self.demo).count(),
        )
        self.assertEqual(
            Note.objects.filter(project=copy).count(),
            Note.objects.filter(project=self.demo).count(),
        )
        self.assertEqual(
            Comment.objects.filter(task__project=copy).count(),
            Comment.objects.filter(task__project=self.demo).count(),
        )
        counter = TaskCounter.objects.get(project=copy)
        self.assertEqual(counter.next_number, source_tasks.last().number + 1)
        # the copy is editable
        status = Status.objects.filter(project=copy).first()
        priority = Priority.objects.filter(project=copy).first()
        response = self.post(
            f"/api/projects/{copy.pk}/tasks/",
            {"title": "Mine", "status": str(status.pk), "priority": str(priority.pk)},
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_copy_accepts_a_name(self):
        self.join_demo()
        data = self.copy(name="My sprint").json()["data"]
        self.assertEqual(data["name"], "My sprint")

    def test_copy_cap(self):
        self.join_demo()
        for _ in range(3):
            self.assertEqual(self.copy().status_code, 201)
        response = self.copy()
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "copy_limit_reached")

    def test_only_demo_projects_can_be_copied(self):
        project = self.create_project(name="Mine", task_key="MINE")
        response = self.post(f"/api/projects/{project['id']}/copy/", {})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "copy_not_allowed")

    def test_non_members_cannot_copy(self):
        self.switch("bob@example.com")
        self.assertEqual(self.copy().status_code, 404)


class TourTests(DemoTestCase):
    def test_tour_flag_round_trip(self):
        self.assertFalse(self.get("/api/me/").json()["data"]["tour_completed"])
        response = self.post("/api/me/tour/")
        self.assertTrue(response.json()["data"]["tour_completed"])
        self.assertTrue(self.get("/api/me/").json()["data"]["tour_completed"])
        response = self.delete("/api/me/tour/")
        self.assertFalse(response.json()["data"]["tour_completed"])
