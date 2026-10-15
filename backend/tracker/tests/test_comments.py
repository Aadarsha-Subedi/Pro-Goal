from django.core import mail

from tracker.tests.base import TrackerTestCase


class CommentTests(TrackerTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.task = self.create_task()
        self.base = self.url(f"tasks/{self.task['number']}/comments/")

    def comment(self, body="Looks good") -> dict:
        response = self.post(self.base, {"body": body})
        assert response.status_code == 201, response.content
        return response.json()["data"]

    def test_create_and_list_oldest_first(self):
        self.comment("one")
        self.comment("two")
        bodies = [c["body"] for c in self.get(self.base).json()["data"]["items"]]
        self.assertEqual(bodies, ["one", "two"])

    def test_edit_own_sets_edited_at(self):
        comment = self.comment("first")
        self.assertIsNone(comment["edited_at"])
        response = self.patch(f"{self.base}{comment['id']}/", {"body": "second"})
        data = response.json()["data"]
        self.assertEqual(data["body"], "second")
        self.assertIsNotNone(data["edited_at"])

    def test_member_cannot_touch_others_but_owner_moderates(self):
        comment = self.comment("owner says")
        self.switch("bob@example.com")
        url = f"{self.base}{comment['id']}/"
        self.assertEqual(self.patch(url, {"body": "x"}).status_code, 403)
        self.assertEqual(self.delete(url).status_code, 403)
        mine = self.comment("bob says")
        self.switch("owner@example.com")
        removed = self.delete(f"{self.base}{mine['id']}/")
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(removed.json()["data"]["is_deleted"], True)

    def test_deleted_comment_stays_as_placeholder(self):
        comment = self.comment("secret")
        self.delete(f"{self.base}{comment['id']}/")
        items = self.get(self.base).json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertIsNone(items[0]["body"])
        self.assertTrue(items[0]["is_deleted"])
        again = self.patch(f"{self.base}{comment['id']}/", {"body": "x"})
        self.assertEqual(again.json()["code"], "comment_deleted")

    def test_mentions(self):
        bob = self.user_id("bob@example.com")
        mail.outbox.clear()
        comment = self.comment(f"hi @[user:{bob}]")
        self.assertEqual([m.to for m in mail.outbox], [["bob@example.com"]])
        self.assertIn("tasks/1", mail.outbox[0].body)
        mail.outbox.clear()
        self.patch(f"{self.base}{comment['id']}/", {"body": f"hi again @[user:{bob}]"})
        self.assertEqual(mail.outbox, [])

    def test_comment_on_other_task_is_404(self):
        comment = self.comment()
        other = self.create_task("Other")
        url = self.url(f"tasks/{other['number']}/comments/{comment['id']}/")
        self.assertEqual(self.patch(url, {"body": "x"}).status_code, 404)

    def test_comment_on_deleted_task_is_404(self):
        self.delete(self.url(f"tasks/{self.task['number']}/"))
        self.assertEqual(self.post(self.base, {"body": "x"}).status_code, 404)
