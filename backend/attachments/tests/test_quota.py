from datetime import timedelta

from django.utils import timezone

from accounts.models import User
from attachments.models import Attachment, ProjectStorageUsage, UserStorageUsage
from attachments.tasks import cleanup_pending_attachments, recompute_storage_usage
from attachments.tests.base import PDF, AttachmentTestCase, pdf_bytes
from projects.models import Membership
from tracker.models import Task


class QuotaTests(AttachmentTestCase):
    def set_quota(self, user: str | None = None, user_bytes=None, project_bytes=None):
        owner = User.objects.get(email="owner@example.com")
        UserStorageUsage.objects.get_or_create(user=owner)
        ProjectStorageUsage.objects.get_or_create(project_id=self.pid)
        if user_bytes is not None:
            UserStorageUsage.objects.filter(
                user__email=user or "owner@example.com"
            ).update(quota_bytes=user_bytes)
        if project_bytes is not None:
            ProjectStorageUsage.objects.filter(project_id=self.pid).update(
                quota_bytes=project_bytes
            )

    def test_defaults(self):
        usage = self.my_usage()
        self.assertEqual(usage["quota_bytes"], 100 * 1024 * 1024)
        self.assertEqual(self.project_usage()["quota_bytes"], 1024 * 1024 * 1024)

    def test_pending_reserves_and_confirm_keeps_it(self):
        data = pdf_bytes(1000)
        attachment = self.upload(data, content_type=PDF, filename="a.pdf")
        self.assertEqual(self.my_usage()["bytes_used"], 1000)
        self.assertEqual(self.project_usage()["bytes_used"], 1000)
        self.confirm(attachment["id"])
        self.assertEqual(self.my_usage()["bytes_used"], 1000)

    def test_user_quota_refuses_with_its_own_code(self):
        self.set_quota(user_bytes=1500)
        self.assertEqual(self.request_upload("a.pdf", PDF, 1000).status_code, 201)
        refused = self.request_upload("b.pdf", PDF, 600)
        self.assertEqual(refused.status_code, 409)
        self.assertEqual(refused.json()["code"], "user_quota_exceeded")
        self.assertEqual(self.my_usage()["bytes_used"], 1000)
        # Exactly filling the quota is fine.
        self.assertEqual(self.request_upload("c.pdf", PDF, 500).status_code, 201)

    def test_project_quota_refuses_and_rolls_back_the_user_counter(self):
        self.set_quota(project_bytes=1200)
        self.request_upload("a.pdf", PDF, 1000)
        refused = self.request_upload("b.pdf", PDF, 500)
        self.assertEqual(refused.json()["code"], "project_quota_exceeded")
        self.assertEqual(self.my_usage()["bytes_used"], 1000)
        self.assertEqual(Attachment.objects.count(), 1)

    def test_user_quota_spans_projects(self):
        self.set_quota(user_bytes=1500)
        self.request_upload("a.pdf", PDF, 1000)
        other = self.create_project(name="Other", task_key="OTH")
        task = self.post(f"/api/projects/{other['id']}/tasks/", {"title": "t"}).json()[
            "data"
        ]
        response = self.post(
            f"/api/projects/{other['id']}/attachments/upload-url/",
            {
                "target_type": "task",
                "target": str(task["number"]),
                "filename": "b.pdf",
                "content_type": PDF,
                "size": 600,
            },
        )
        self.assertEqual(response.json()["code"], "user_quota_exceeded")
        usage = self.my_usage()
        self.assertEqual([p["project_name"] for p in usage["by_project"]], ["Apollo"])

    def test_each_user_has_their_own_allowance(self):
        self.set_quota(user_bytes=1000)
        self.request_upload("a.pdf", PDF, 1000)
        self.switch("bob@example.com")
        self.assertEqual(self.request_upload("b.pdf", PDF, 1000).status_code, 201)

    def test_delete_frees_quota_and_object(self):
        data = pdf_bytes(800)
        attachment = self.attach(data, content_type=PDF, filename="a.pdf")
        key = self.key_of(attachment)
        self.assertIn(key, self.storage.objects)
        self.assertEqual(
            self.delete(self.url(f"attachments/{attachment['id']}/")).status_code, 200
        )
        self.assertNotIn(key, self.storage.objects)
        self.assertEqual(self.my_usage()["bytes_used"], 0)
        self.assertEqual(self.project_usage()["bytes_used"], 0)

    def test_breakdowns(self):
        self.attach(pdf_bytes(500), content_type=PDF, filename="a.pdf")
        self.switch("bob@example.com")
        self.attach(pdf_bytes(300), content_type=PDF, filename="b.pdf")
        self.switch("owner@example.com")
        usage = self.project_usage()
        self.assertEqual(usage["bytes_used"], 800)
        self.assertEqual(usage["by_category"], {"document": 800})
        self.assertEqual(
            [(u["first_name"], u["bytes"]) for u in usage["by_uploader"]],
            [("Ada", 500), ("Bob", 300)],
        )

    def test_pending_cleanup_after_a_day(self):
        stale = self.upload(pdf_bytes(400), content_type=PDF, filename="a.pdf")
        fresh = self.upload(pdf_bytes(100), content_type=PDF, filename="b.pdf")
        Attachment.objects.filter(pk=stale["id"]).update(
            created_at=timezone.now() - timedelta(hours=25)
        )
        stale_key = self.key_of(stale)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(cleanup_pending_attachments.delay().get(), 1)
        self.assertNotIn(stale_key, self.storage.objects)
        self.assertEqual(
            [str(p) for p in Attachment.objects.values_list("pk", flat=True)],
            [fresh["id"]],
        )
        self.assertEqual(self.my_usage()["bytes_used"], 100)

    def test_recompute_repairs_drift(self):
        self.attach(pdf_bytes(500), content_type=PDF, filename="a.pdf")
        UserStorageUsage.objects.update(bytes_used=9999)
        ProjectStorageUsage.objects.update(bytes_used=1)
        recompute_storage_usage.delay().get()
        self.assertEqual(self.my_usage()["bytes_used"], 500)
        self.assertEqual(self.project_usage()["bytes_used"], 500)

    def test_removed_uploader_keeps_project_total_but_not_user_usage(self):
        self.switch("bob@example.com")
        self.attach(pdf_bytes(300), content_type=PDF, filename="b.pdf")
        self.switch("owner@example.com")
        Membership.objects.filter(user__email="bob@example.com").delete()
        User.objects.filter(email="bob@example.com").delete()
        self.assertEqual(self.project_usage()["bytes_used"], 300)
        row = Attachment.objects.get()
        self.assertIsNone(row.uploaded_by)
        self.assertEqual(
            self.project_usage()["by_uploader"][0]["first_name"], "Deleted user"
        )
        recompute_storage_usage.delay().get()
        self.assertEqual(self.project_usage()["bytes_used"], 300)

    def test_task_purge_removes_objects_and_frees_quota(self):
        from tracker.tasks import purge_deleted_tasks

        attachment = self.attach(pdf_bytes(700), content_type=PDF, filename="a.pdf")
        key = self.key_of(attachment)
        self.delete(self.url(f"tasks/{self.task['number']}/"))
        # A soft-deleted task keeps its files (and their quota) for now.
        self.assertIn(key, self.storage.objects)
        self.assertEqual(self.my_usage()["bytes_used"], 700)
        Task.all_objects.update(deleted_at=timezone.now() - timedelta(days=8))
        with self.captureOnCommitCallbacks(execute=True):
            purge_deleted_tasks.delay().get()
        self.assertNotIn(key, self.storage.objects)
        self.assertEqual(Attachment.objects.count(), 0)
        self.assertEqual(self.my_usage()["bytes_used"], 0)

    def test_project_purge_removes_objects(self):
        from projects.models import Project
        from projects.tasks import purge_deleted_projects

        attachment = self.attach(pdf_bytes(700), content_type=PDF, filename="a.pdf")
        key = self.key_of(attachment)
        Project.all_objects.filter(pk=self.pid).update(
            is_deleted=True, deleted_at=timezone.now() - timedelta(days=8)
        )
        with self.captureOnCommitCallbacks(execute=True):
            purge_deleted_projects.delay().get()
        self.assertNotIn(key, self.storage.objects)
        self.assertEqual(self.my_usage()["bytes_used"], 0)
