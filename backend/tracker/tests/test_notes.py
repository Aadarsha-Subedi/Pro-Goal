from django.core import mail

from projects.models import Tag
from tracker.models import Note, NoteRevision
from tracker.tests.base import TrackerTestCase


class NoteTests(TrackerTestCase):
    def create_note(self, title="Design", body="v1", **extra) -> dict:
        response = self.post(
            self.url("notes/"), {"title": title, "body": body, **extra}
        )
        assert response.status_code == 201, response.content
        return response.json()["data"]

    def test_create_writes_first_revision(self):
        note = self.create_note(tags=["Arch", "arch"])
        self.assertEqual(
            (note["version"], note["tags"], note["body"]), (1, ["arch"], "v1")
        )
        revisions = self.items(f"notes/{note['id']}/revisions/")
        self.assertEqual([r["version"] for r in revisions], [1])
        self.assertEqual(Tag.objects.get(name="arch").usage_count, 1)

    def test_update_bumps_version_and_keeps_history(self):
        note = self.create_note()
        url = self.url(f"notes/{note['id']}/")
        response = self.patch(url, {"version": 1, "body": "v2", "title": "Design 2"})
        self.assertEqual(response.json()["data"]["version"], 2)
        revisions = self.items(f"notes/{note['id']}/revisions/")
        self.assertEqual(
            [(r["version"], r["body"]) for r in revisions], [(2, "v2"), (1, "v1")]
        )

    def test_stale_version_is_refused(self):
        note = self.create_note()
        url = self.url(f"notes/{note['id']}/")
        self.patch(url, {"version": 1, "body": "mine"})
        stale = self.patch(url, {"version": 1, "body": "theirs"})
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["code"], "stale_data")
        self.assertEqual(self.get(url).json()["data"]["body"], "mine")

    def test_noop_and_tag_only_updates(self):
        note = self.create_note()
        url = self.url(f"notes/{note['id']}/")
        same = self.patch(url, {"version": 1, "body": "v1"})
        self.assertEqual(same.json()["data"]["version"], 1)
        tagged = self.patch(url, {"version": 1, "tags": ["x"]})
        self.assertEqual(tagged.json()["data"]["version"], 1)
        self.assertEqual(tagged.json()["data"]["tags"], ["x"])
        self.assertEqual(NoteRevision.objects.filter(note_id=note["id"]).count(), 1)

    def test_version_is_required(self):
        note = self.create_note()
        response = self.patch(self.url(f"notes/{note['id']}/"), {"body": "x"})
        self.assertEqual(response.status_code, 400)

    def test_body_size_limit(self):
        big = "x" * (100 * 1024 + 1)
        response = self.post(self.url("notes/"), {"title": "Big", "body": big})
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["code"], "note_too_large")

    def test_list_search_and_detail_shape(self):
        self.create_note("Roadmap", tags=["plan"])
        self.create_note("Retro")
        listing = self.items("notes/", q="road")
        self.assertEqual([n["title"] for n in listing], ["Roadmap"])
        self.assertNotIn("body", listing[0])
        self.assertEqual(
            [n["title"] for n in self.items("notes/", tag="PLAN")], ["Roadmap"]
        )

    def test_delete_needs_the_grant(self):
        owners = self.create_note("Owner note")
        self.switch("bob@example.com")
        mine = self.create_note("Bob note")
        # Even your own note needs note.delete; Contributor does not include it.
        self.assertEqual(
            self.delete(self.url(f"notes/{owners['id']}/")).status_code, 403
        )
        self.assertEqual(self.delete(self.url(f"notes/{mine['id']}/")).status_code, 403)
        self.switch("owner@example.com")
        self.put(
            self.url(f"members/{self.user_id('bob@example.com')}/permissions/"),
            {"permissions": ["note.create", "note.delete"]},
        )
        self.switch("bob@example.com")
        self.assertEqual(self.delete(self.url(f"notes/{mine['id']}/")).status_code, 200)
        self.assertEqual(
            self.delete(self.url(f"notes/{owners['id']}/")).status_code, 200
        )
        self.assertEqual(Note.objects.count(), 0)
        self.assertEqual(NoteRevision.objects.count(), 0)

    def test_link_and_unlink(self):
        task = self.create_task()
        note = self.create_note()
        base = self.url(f"tasks/{task['number']}/notes/")
        self.assertEqual(self.put(f"{base}{note['id']}/").status_code, 200)
        self.assertEqual(
            self.put(f"{base}{note['id']}/").status_code, 200
        )  # idempotent
        self.assertEqual(
            [n["id"] for n in self.items(f"tasks/{task['number']}/notes/")],
            [note["id"]],
        )
        self.assertEqual(self.delete(f"{base}{note['id']}/").status_code, 200)
        self.assertEqual(self.items(f"tasks/{task['number']}/notes/"), [])

    def test_link_note_from_another_project_is_404(self):
        other = self.create_project(name="Other", task_key="OTH")
        foreign = self.post(
            f"/api/projects/{other['id']}/notes/", {"title": "x"}
        ).json()["data"]
        task = self.create_task()
        response = self.put(self.url(f"tasks/{task['number']}/notes/{foreign['id']}/"))
        self.assertEqual(response.status_code, 404)

    def test_mentions_notify_new_members_only(self):
        bob = self.user_id("bob@example.com")
        outsider = str(self.make_user("eve@example.com").pk)
        mail.outbox.clear()
        note = self.create_note(body=f"cc @[user:{bob}] and @[user:{outsider}]")
        self.assertEqual([m.to for m in mail.outbox], [["bob@example.com"]])
        mail.outbox.clear()
        url = self.url(f"notes/{note['id']}/")
        self.patch(url, {"version": 1, "body": f"cc @[user:{bob}] again"})
        self.assertEqual(mail.outbox, [])  # Bob was already mentioned
        owner = self.user_id("owner@example.com")
        self.patch(url, {"version": 2, "body": f"@[user:{bob}] @[user:{owner}]"})
        self.assertEqual(mail.outbox, [])  # no self mention, no repeat

    def test_archived_project_is_read_only(self):
        note = self.create_note()
        self.post(self.url("archive/"))
        response = self.patch(
            self.url(f"notes/{note['id']}/"), {"version": 1, "body": "x"}
        )
        self.assertEqual(response.json()["code"], "project_archived")
