from accounts.models import User
from projects.models import Membership
from tracker.models import Comment, Note, Task, TaskAssignee
from tracker.tests.base import TrackerTestCase


class KanbanPreferenceTests(TrackerTestCase):
    def test_defaults_then_save_per_user(self):
        url = self.url("kanban-preference/")
        self.assertEqual(
            self.get(url).json()["data"], {"group_by": "status", "sort_by": "number"}
        )
        saved = self.put(url, {"group_by": "assignee", "sort_by": "due_date"})
        self.assertEqual(saved.json()["data"]["group_by"], "assignee")
        self.assertEqual(self.get(url).json()["data"]["sort_by"], "due_date")
        self.put(url, {"group_by": "tag", "sort_by": "title"})
        self.assertEqual(self.get(url).json()["data"]["group_by"], "tag")
        # Another member keeps their own setup.
        self.switch("bob@example.com")
        self.assertEqual(self.get(url).json()["data"]["group_by"], "status")

    def test_invalid_values_rejected(self):
        url = self.url("kanban-preference/")
        for body in (
            {"group_by": "due_date", "sort_by": "number"},  # dates cannot group
            {"group_by": "status", "sort_by": "nope"},
            {"group_by": "status"},
        ):
            self.assertEqual(self.put(url, body).status_code, 400)


class ReassignmentTests(TrackerTestCase):
    def remove_bob(self, reassign: dict):
        return self.client.delete(
            self.url(f"members/{self.user_id('bob@example.com')}/"),
            {"reassign": reassign},
            format="json",
            **self._headers(),
        )

    def test_removing_a_member_moves_assignments_and_notes(self):
        bob = self.user_id("bob@example.com")
        owner = self.user_id("owner@example.com")
        self.create_task("Bob's work", assignees=[bob])
        self.create_task("Shared", assignees=[bob, owner])
        self.post(self.url("notes/"), {"title": "n"})
        self.switch("bob@example.com")
        bobs_note = self.post(self.url("notes/"), {"title": "bob note"}).json()["data"]
        self.switch("owner@example.com")

        response = self.remove_bob({"tasks": owner, "notes": owner})
        self.assertEqual(response.status_code, 200)
        by_title = {t["title"]: t for t in self.items("tasks/")}
        self.assertEqual(
            [a["id"] for a in by_title["Bob's work"]["assignees"]], [owner]
        )
        self.assertEqual([a["id"] for a in by_title["Shared"]["assignees"]], [owner])
        self.assertEqual(
            Note.objects.get(pk=bobs_note["id"]).author_id.hex, owner.replace("-", "")
        )

    def test_unmapped_items_become_unassigned_but_history_stays(self):
        bob = self.user_id("bob@example.com")
        self.switch("bob@example.com")
        task = self.create_task("Bob's", assignees=[bob])
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "hi"})
        note = self.post(self.url("notes/"), {"title": "n"}).json()["data"]
        self.switch("owner@example.com")
        self.assertEqual(self.remove_bob({}).status_code, 200)
        detail = self.get(self.url(f"tasks/{task['number']}/")).json()["data"]
        self.assertEqual(detail["assignees"], [])
        self.assertEqual(detail["created_by"]["first_name"], "Bob")
        self.assertEqual(Comment.objects.get().author.email, "bob@example.com")
        self.assertEqual(
            Note.objects.get(pk=note["id"]).author.email, "bob@example.com"
        )

    def test_unknown_reassign_key_is_still_rejected(self):
        response = self.remove_bob({"widgets": self.user_id("owner@example.com")})
        self.assertEqual(response.json()["code"], "invalid_reassignment")


class DeletedAccountTests(TrackerTestCase):
    def test_hard_deleted_author_shows_as_deleted_user(self):
        self.switch("bob@example.com")
        task = self.create_task("From Bob")
        self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "hello"})
        note = self.post(self.url("notes/"), {"title": "bobs"}).json()["data"]
        self.switch("owner@example.com")
        Membership.objects.filter(user__email="bob@example.com").delete()
        User.objects.filter(email="bob@example.com").delete()

        detail = self.get(self.url(f"tasks/{task['number']}/")).json()["data"]
        self.assertEqual(detail["created_by"]["first_name"], "Deleted user")
        comment = self.get(self.url(f"tasks/{task['number']}/comments/")).json()[
            "data"
        ]["items"][0]
        self.assertEqual(comment["author"]["first_name"], "Deleted user")
        self.assertEqual(comment["body"], "hello")
        shown = self.get(self.url(f"notes/{note['id']}/")).json()["data"]
        self.assertEqual(shown["author"]["first_name"], "Deleted user")
        self.assertEqual(Task.all_objects.count(), 1)
        self.assertEqual(TaskAssignee.objects.count(), 0)
