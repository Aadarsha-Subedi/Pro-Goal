from projects.models import Project
from tracker.models import Priority, Status, TaskCounter
from tracker.tests.base import TrackerTestCase


class SeedingTests(TrackerTestCase):
    def test_new_project_is_seeded(self):
        statuses = self.items("statuses/")
        self.assertEqual(
            [(s["name"], s["category"]) for s in statuses],
            [
                ("To do", "todo"),
                ("In progress", "in_progress"),
                ("In review", "in_progress"),
                ("Done", "done"),
                ("Cancelled", "done"),
            ],
        )
        self.assertEqual([s["name"] for s in statuses if s["is_default"]], ["To do"])
        priorities = self.items("priorities/")
        self.assertEqual(
            [p["name"] for p in priorities], ["Low", "Medium", "High", "Urgent"]
        )
        self.assertEqual([p["rank"] for p in priorities], [1, 2, 3, 4])
        self.assertEqual([p["name"] for p in priorities if p["is_default"]], ["Medium"])
        self.assertTrue(TaskCounter.objects.filter(project_id=self.pid).exists())

    def test_seed_is_idempotent(self):
        from tracker.services.seeding import seed_project_defaults

        seed_project_defaults(Project.objects.get(pk=self.pid))
        self.assertEqual(Status.objects.filter(project_id=self.pid).count(), 5)
        self.assertEqual(Priority.objects.filter(project_id=self.pid).count(), 4)

    def test_backfill_migration_seeds_existing_projects(self):
        import importlib

        from django.apps import apps

        migration = importlib.import_module(
            "tracker.migrations.0002_backfill_project_defaults"
        )
        Status.objects.filter(project_id=self.pid).delete()
        Priority.objects.filter(project_id=self.pid).delete()
        migration.backfill(apps, None)
        self.assertEqual(Status.objects.filter(project_id=self.pid).count(), 5)
        self.assertEqual(Priority.objects.filter(project_id=self.pid).count(), 4)
        self.assertEqual(
            Status.objects.filter(project_id=self.pid, is_default=True).count(), 1
        )

    def test_non_member_cannot_read(self):
        outsider = self.make_user("eve@example.com")
        self.switch("eve@example.com")
        self.assertEqual(self.get(self.url("statuses/")).status_code, 404)
        self.assertIsNotNone(outsider)


class StatusTests(TrackerTestCase):
    def test_create_rename_reorder_default(self):
        created = self.post(
            self.url("statuses/"), {"name": "Blocked", "category": "in_progress"}
        )
        self.assertEqual(created.status_code, 201)
        sid = created.json()["data"]["id"]
        self.assertEqual(self.items("statuses/")[-1]["name"], "Blocked")

        self.patch(self.url(f"statuses/{sid}/"), {"position": 0, "name": "Blocked!"})
        first = self.items("statuses/")[0]
        self.assertEqual((first["name"], first["position"]), ("Blocked!", 0))
        self.assertEqual(
            [s["position"] for s in self.items("statuses/")], [0, 1, 2, 3, 4, 5]
        )

        self.patch(self.url(f"statuses/{sid}/"), {"is_default": True})
        defaults = [s["name"] for s in self.items("statuses/") if s["is_default"]]
        self.assertEqual(defaults, ["Blocked!"])

    def test_duplicate_name_case_insensitive(self):
        response = self.post(
            self.url("statuses/"), {"name": "done", "category": "done"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "duplicate_name")

    def test_member_cannot_manage(self):
        self.switch("bob@example.com")
        self.assertEqual(
            self.post(
                self.url("statuses/"), {"name": "X", "category": "todo"}
            ).status_code,
            403,
        )
        self.assertEqual(self.items("statuses/")[0]["name"], "To do")  # reading is open

    def test_delete_unused_and_guards(self):
        sid = self.status_id("Cancelled")
        self.assertEqual(self.delete(self.url(f"statuses/{sid}/")).status_code, 200)
        # "Done" is now the only done-category status.
        done = self.delete(self.url(f"statuses/{self.status_id('Done')}/"))
        self.assertEqual(done.json()["code"], "last_in_category")
        default = self.delete(self.url(f"statuses/{self.status_id('To do')}/"))
        self.assertEqual(default.json()["code"], "cannot_delete_default")

    def test_delete_in_use_needs_replacement(self):
        task = self.create_task(status=self.status_id("In review"))
        sid = self.status_id("In review")
        needs = self.delete(self.url(f"statuses/{sid}/"))
        self.assertEqual(needs.json()["code"], "in_use_needs_replacement")
        bad = self.client.delete(
            self.url(f"statuses/{sid}/"),
            {"move_to": sid},
            format="json",
            **self._headers(),
        )
        self.assertEqual(bad.json()["code"], "invalid_replacement")
        ok = self.client.delete(
            self.url(f"statuses/{sid}/"),
            {"move_to": self.status_id("In progress")},
            format="json",
            **self._headers(),
        )
        self.assertEqual(ok.status_code, 200)
        moved = self.get(self.url(f"tasks/{task['number']}/")).json()["data"]
        self.assertEqual(moved["status"]["name"], "In progress")

    def test_cannot_move_last_status_out_of_category(self):
        todo = self.status_id("To do")
        response = self.patch(self.url(f"statuses/{todo}/"), {"category": "done"})
        self.assertEqual(response.json()["code"], "last_in_category")

    def test_archived_project_is_read_only(self):
        self.post(self.url("archive/"))
        response = self.post(self.url("statuses/"), {"name": "X", "category": "todo"})
        self.assertEqual(response.json()["code"], "project_archived")


class PriorityTests(TrackerTestCase):
    def test_create_move_default_and_ranks(self):
        created = self.post(
            self.url("priorities/"), {"name": "Critical", "position": 0}
        )
        pid = created.json()["data"]["id"]
        names = [(p["name"], p["rank"]) for p in self.items("priorities/")]
        self.assertEqual(names[0], ("Critical", 1))
        self.assertEqual(names[-1], ("Urgent", 5))
        self.patch(self.url(f"priorities/{pid}/"), {"is_default": True})
        self.assertEqual(
            [p["name"] for p in self.items("priorities/") if p["is_default"]],
            ["Critical"],
        )

    def test_delete_in_use_and_default(self):
        self.create_task(priority=self.priority_id("High"))
        high = self.priority_id("High")
        self.assertEqual(
            self.delete(self.url(f"priorities/{high}/")).json()["code"],
            "in_use_needs_replacement",
        )
        self.client.delete(
            self.url(f"priorities/{high}/"),
            {"move_to": self.priority_id("Low")},
            format="json",
            **self._headers(),
        )
        self.assertEqual(self.items("tasks/")[0]["priority"]["name"], "Low")
        default = self.delete(self.url(f"priorities/{self.priority_id('Medium')}/"))
        self.assertEqual(default.json()["code"], "cannot_delete_default")

    def test_member_cannot_manage(self):
        self.switch("bob@example.com")
        self.assertEqual(
            self.post(self.url("priorities/"), {"name": "X"}).status_code, 403
        )
