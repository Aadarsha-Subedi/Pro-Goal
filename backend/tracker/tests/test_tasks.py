from datetime import timedelta

from django.utils import timezone

from projects.models import ActivityLog, Tag
from tracker.models import Task
from tracker.tasks import purge_deleted_tasks
from tracker.tests.base import TrackerTestCase


class TaskCrudTests(TrackerTestCase):
    def test_create_defaults_and_numbers(self):
        first = self.create_task("One")
        second = self.create_task("Two", tags=[" Bug ", "bug"], description="# hi")
        self.assertEqual((first["number"], second["number"]), (1, 2))
        self.assertEqual(first["key"], "APL-1")
        self.assertEqual(first["project"]["task_key"], "APL")
        self.assertEqual(first["status"]["name"], "To do")
        self.assertEqual(first["priority"]["name"], "Medium")
        self.assertEqual(second["tags"], ["bug"])
        self.assertEqual(second["description"], "# hi")
        self.assertEqual(Tag.objects.get(name="bug").usage_count, 1)
        self.assertTrue(ActivityLog.objects.filter(action="task.created").exists())

    def test_numbers_are_per_project(self):
        other = self.create_project(name="Other", task_key="OTH")
        response = self.post(f"/api/projects/{other['id']}/tasks/", {"title": "x"})
        self.assertEqual(response.json()["data"]["number"], 1)

    def test_member_can_create_and_edit(self):
        self.switch("bob@example.com")
        task = self.create_task("Bob's task")
        response = self.patch(
            self.url(f"tasks/{task['number']}/"), {"title": "Renamed"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["title"], "Renamed")
        self.assertEqual(response.json()["data"]["created_by"]["first_name"], "Bob")

    def test_validation(self):
        bad_dates = self.post(
            self.url("tasks/"),
            {"title": "x", "start_date": "2026-05-02", "due_date": "2026-05-01"},
        )
        self.assertEqual(bad_dates.json()["code"], "invalid_date_range")
        unknown_status = self.post(
            self.url("tasks/"),
            {"title": "x", "status": "00000000-0000-0000-0000-000000000000"},
        )
        self.assertEqual(unknown_status.status_code, 404)
        extra = self.post(self.url("tasks/"), {"title": "x", "number": 9})
        self.assertEqual(extra.status_code, 400)

    def test_update_changes_are_logged(self):
        task = self.create_task()
        url = self.url(f"tasks/{task['number']}/")
        response = self.patch(
            url,
            {
                "status": self.status_id("In progress"),
                "priority": self.priority_id("Urgent"),
                "due_date": "2030-01-01",
                "tags": ["a"],
            },
        )
        data = response.json()["data"]
        self.assertEqual(data["status"]["name"], "In progress")
        self.assertEqual(data["priority"]["name"], "Urgent")
        self.assertEqual(data["tags"], ["a"])
        log = ActivityLog.objects.filter(action="task.updated").latest("created_at")
        self.assertEqual(log.changes["status"], {"from": "To do", "to": "In progress"})

    def test_task_addressed_by_number_survives_key_change(self):
        task = self.create_task()
        self.patch(self.url(), {"task_key": "NEW"})
        detail = self.get(self.url(f"tasks/{task['number']}/")).json()["data"]
        self.assertEqual(detail["key"], "NEW-1")

    def test_non_member_and_missing(self):
        task = self.create_task()
        self.make_user("eve@example.com")
        self.switch("eve@example.com")
        self.assertEqual(
            self.get(self.url(f"tasks/{task['number']}/")).status_code, 404
        )
        self.switch("owner@example.com")
        self.assertEqual(self.get(self.url("tasks/99/")).status_code, 404)

    def test_archived_project_is_read_only(self):
        task = self.create_task()
        self.post(self.url("archive/"))
        self.assertEqual(
            self.post(self.url("tasks/"), {"title": "x"}).json()["code"],
            "project_archived",
        )
        self.assertEqual(
            self.patch(
                self.url(f"tasks/{task['number']}/"), {"title": "y"}
            ).status_code,
            409,
        )
        self.assertEqual(
            self.get(self.url(f"tasks/{task['number']}/")).status_code, 200
        )


class AssigneeTests(TrackerTestCase):
    def test_assign_members_only(self):
        bob = self.user_id("bob@example.com")
        task = self.create_task(assignees=[bob])
        self.assertEqual([a["id"] for a in task["assignees"]], [bob])
        stranger = str(self.make_user("eve@example.com").pk)
        response = self.patch(
            self.url(f"tasks/{task['number']}/"), {"assignees": [stranger]}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "assignee_not_member")
        cleared = self.patch(self.url(f"tasks/{task['number']}/"), {"assignees": []})
        self.assertEqual(cleared.json()["data"]["assignees"], [])


class SubtaskTests(TrackerTestCase):
    def test_subtask_flow_and_rules(self):
        parent = self.create_task("Parent")
        n = parent["number"]
        sub = self.post(self.url(f"tasks/{n}/subtasks/"), {"title": "Child"})
        self.assertEqual(sub.status_code, 201)
        child = sub.json()["data"]
        self.assertEqual(child["parent_number"], n)

        parent_detail = self.get(self.url(f"tasks/{n}/")).json()["data"]
        self.assertEqual(parent_detail["subtasks"], {"total": 1, "done": 0})
        self.assertEqual(len(self.items(f"tasks/{n}/subtasks/")), 1)

        # One level only.
        deep = self.post(self.url(f"tasks/{child['number']}/subtasks/"), {"title": "x"})
        self.assertEqual(deep.json()["code"], "subtask_of_subtask")

        # Parent cannot be Done while a subtask is open.
        done = self.status_id("Done")
        blocked = self.patch(self.url(f"tasks/{n}/"), {"status": done})
        self.assertEqual(blocked.json()["code"], "open_subtasks")
        self.patch(self.url(f"tasks/{child['number']}/"), {"status": done})
        ok = self.patch(self.url(f"tasks/{n}/"), {"status": done})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(
            self.get(self.url(f"tasks/{n}/")).json()["data"]["subtasks"],
            {"total": 1, "done": 1},
        )

    def test_parent_changes(self):
        a, b = self.create_task("A"), self.create_task("B")
        self.post(self.url(f"tasks/{a['number']}/subtasks/"), {"title": "child"})
        # A has a subtask, so it cannot become one.
        response = self.patch(
            self.url(f"tasks/{a['number']}/"), {"parent": b["number"]}
        )
        self.assertEqual(response.json()["code"], "task_has_subtasks")
        # Self and unknown parents are rejected.
        own = self.patch(self.url(f"tasks/{b['number']}/"), {"parent": b["number"]})
        self.assertEqual(own.json()["code"], "invalid_parent")
        # Make B a subtask of A? A is top level, B has no subtasks: allowed. Then promote back.
        moved = self.patch(self.url(f"tasks/{b['number']}/"), {"parent": a["number"]})
        self.assertEqual(moved.json()["data"]["parent_number"], a["number"])
        promoted = self.patch(self.url(f"tasks/{b['number']}/"), {"parent": None})
        self.assertIsNone(promoted.json()["data"]["parent_number"])


class DeleteRestoreTests(TrackerTestCase):
    def test_delete_cascades_to_subtasks_and_restores_together(self):
        parent = self.create_task("Parent")
        n = parent["number"]
        self.post(self.url(f"tasks/{n}/subtasks/"), {"title": "kid1"})
        kept = self.post(self.url(f"tasks/{n}/subtasks/"), {"title": "kid2"}).json()[
            "data"
        ]
        self.delete(self.url(f"tasks/{kept['number']}/"))  # deleted earlier, separately
        deleted = self.delete(self.url(f"tasks/{n}/"))
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(self.items("tasks/"), [])
        self.assertEqual(self.get(self.url(f"tasks/{n}/")).status_code, 404)

        restored = self.post(self.url(f"tasks/{n}/restore/"))
        self.assertEqual(restored.status_code, 200)
        titles = sorted(t["title"] for t in self.items("tasks/"))
        # kid2 was deleted before the parent, so it stays deleted.
        self.assertEqual(titles, ["Parent", "kid1"])

    def test_restore_rules(self):
        task = self.create_task()
        n = task["number"]
        self.assertEqual(
            self.post(self.url(f"tasks/{n}/restore/")).json()["code"],
            "task_not_deleted",
        )
        self.delete(self.url(f"tasks/{n}/"))
        Task.all_objects.update(deleted_at=timezone.now() - timedelta(days=8))
        late = self.post(self.url(f"tasks/{n}/restore/"))
        self.assertEqual(late.json()["code"], "task_restore_window_over")
        self.assertEqual(purge_deleted_tasks.delay().get(), 1)
        self.assertEqual(Task.all_objects.count(), 0)

    def test_deleting_needs_the_grant_even_for_the_creator(self):
        owners = self.create_task("Owner's")
        self.switch("bob@example.com")
        mine = self.create_task("Bob's")
        self.assertEqual(
            self.delete(self.url(f"tasks/{owners['number']}/")).status_code, 403
        )
        self.assertEqual(
            self.delete(self.url(f"tasks/{mine['number']}/")).status_code, 403
        )
        self.switch("owner@example.com")
        self.put(
            self.url(f"members/{self.user_id('bob@example.com')}/permissions/"),
            {"permissions": ["task.create", "task.delete"]},
        )
        self.switch("bob@example.com")
        self.assertEqual(
            self.delete(self.url(f"tasks/{owners['number']}/")).status_code, 200
        )
        self.assertEqual(
            self.post(self.url(f"tasks/{owners['number']}/restore/")).status_code, 200
        )

    def test_purge_releases_tag_counts(self):
        task = self.create_task(tags=["x"])
        self.delete(self.url(f"tasks/{task['number']}/"))
        Task.all_objects.update(deleted_at=timezone.now() - timedelta(days=8))
        purge_deleted_tasks.delay().get()
        self.assertEqual(Tag.objects.get(name="x").usage_count, 0)


class ProjectPurgeTests(TrackerTestCase):
    def test_purging_a_project_with_tasks_works(self):
        from projects.models import Project
        from projects.tasks import purge_deleted_projects

        self.create_task("A")
        self.create_task("B")
        Project.all_objects.filter(pk=self.pid).update(
            is_deleted=True, deleted_at=timezone.now() - timedelta(days=8)
        )
        self.assertEqual(purge_deleted_projects.delay().get(), 1)
        self.assertEqual(Task.all_objects.count(), 0)
