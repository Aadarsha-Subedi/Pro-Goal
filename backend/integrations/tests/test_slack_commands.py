from integrations.models import InboundWebhook, OutboxEvent
from integrations.slack import commands
from integrations.tests.slack_base import HOOK, SlackTestCase
from tracker.models import Task


class ParseTests(SlackTestCase):
    def test_parse(self):
        self.assertEqual(
            commands.parse("create PMS Fix the login"),
            ("create", "PMS", "Fix the login"),
        )
        self.assertEqual(
            commands.parse("  create pms   Spaced   title  "),
            ("create", "PMS", "Spaced   title"),
        )
        self.assertEqual(commands.parse("done PMS-42"), ("done", "PMS", 42))
        self.assertEqual(commands.parse("done pms-7"), ("done", "PMS", 7))
        for bad in (
            "",
            "create",
            "create PMS",
            "done",
            "done PMS",
            "done 42",
            "remove PMS-1",
            "create P x",
        ):
            self.assertIsNone(commands.parse(bad), bad)


class CommandTests(SlackTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.link_user("owner@example.com", "UPERSON")

    def test_create_makes_the_task_as_the_linked_user_and_replies_privately(self):
        response = self.command("create APL Fix the login page")
        self.assertEqual(response.status_code, 200)
        task = Task.objects.get(title="Fix the login page")
        self.assertEqual(task.created_by.email, "owner@example.com")
        self.assertEqual(task.number, 1)
        reply = self.hub.replies[-1]
        self.assertEqual(reply["response_type"], "ephemeral")
        self.assertEqual(reply["url"], HOOK)
        self.assertIn("Created *APL-1* Fix the login page", reply["text"])
        self.assertIn(f"/projects/{self.pid}/tasks/1", reply["text"])

    def test_the_change_is_tagged_slack_and_not_posted_back_to_slack(self):
        self.map_channel("C1", ["task_created"])
        self.command("create APL From slack")
        self.assertEqual(
            OutboxEvent.objects.get(event_type="task_created").source, "slack"
        )
        self.assertEqual(self.hub.posts, [])
        self.create_task("From the web")
        self.assertEqual(len(self.hub.posts), 1)

    def test_done_moves_the_task_to_the_first_done_status(self):
        task = self.create_task("Finish me")
        self.command(f"done APL-{task['number']}", trigger="t2")
        done = Task.objects.get(number=task["number"])
        self.assertEqual((done.status.name, done.status.category), ("Done", "done"))
        self.assertIn(
            f"Marked *APL-{task['number']}* Finish me as done", self.last_reply
        )

    def test_done_twice_and_unknown_task(self):
        task = self.create_task("Once")
        self.command(f"done APL-{task['number']}", trigger="a")
        self.command(f"done APL-{task['number']}", trigger="b")
        self.assertIn("already done", self.last_reply)
        self.command("done APL-999", trigger="c")
        self.assertIn("could not find task *APL-999*", self.last_reply)

    def test_done_respects_the_open_subtasks_rule(self):
        parent = self.create_task("Parent")
        self.post(self.url(f"tasks/{parent['number']}/subtasks/"), {"title": "Child"})
        self.command(f"done APL-{parent['number']}")
        self.assertIn("Finish or cancel every subtask first", self.last_reply)
        self.assertEqual(
            Task.objects.get(number=parent["number"]).status.category, "todo"
        )

    def test_unlinked_people_are_told_how_to_link(self):
        self.command("create APL Anything", user="USTRANGER")
        self.assertIn("Link your Slack account first", self.last_reply)
        self.assertIn("http://localhost:3000/settings/integrations", self.last_reply)
        self.assertEqual(Task.objects.count(), 0)

    def test_usage_help_for_bad_syntax(self):
        self.command("remove everything")
        self.assertIn("/task create", self.last_reply)
        self.assertIn("/task done", self.last_reply)

    def test_unknown_key_and_projects_in_other_workspaces(self):
        self.command("create NOPE x", trigger="a")
        self.assertIn("could not find a project with key *NOPE*", self.last_reply)
        # The project is connected to a different Slack workspace than the caller's.
        self.link_user("owner@example.com", "UOTHER", team="T-OTHER")
        self.command("create APL x", user="UOTHER", team="T-OTHER", trigger="b")
        self.assertIn("could not find a project", self.last_reply)
        self.assertEqual(Task.objects.count(), 0)

    def test_non_members_cannot_use_a_project_they_are_not_in(self):
        self.make_user("eve@example.com")
        self.link_user("eve@example.com", "UEVE")
        self.command("create APL sneaky", user="UEVE")
        self.assertIn("could not find a project", self.last_reply)
        self.assertEqual(Task.objects.count(), 0)

    def test_two_projects_with_the_same_key_in_one_workspace_are_ambiguous(self):
        other = self.create_project(name="Second", task_key="APL")
        self.connect_slack(project_id=other["id"])
        self.command("create APL x")
        self.assertIn(
            "More than one of your projects uses the key *APL*", self.last_reply
        )
        self.assertIn("Second", self.last_reply)
        self.assertEqual(Task.objects.count(), 0)

    def test_permissions_are_the_linked_users_own(self):
        self.link_user("bob@example.com", "UBOB")
        self.put(
            self.url(f"members/{self.user_id('bob@example.com')}/permissions/"),
            {"permissions": []},
        )
        self.command("create APL nope", user="UBOB", trigger="a")
        self.assertIn("do not have permission", self.last_reply)
        self.assertEqual(Task.objects.count(), 0)
        self.put(
            self.url(f"members/{self.user_id('bob@example.com')}/permissions/"),
            {"permissions": ["task.create"]},
        )
        self.command("create APL now allowed", user="UBOB", trigger="b")
        self.assertEqual(Task.objects.get().title, "now allowed")
        # task.create does not include changing status.
        self.command("done APL-1", user="UBOB", trigger="c")
        self.assertIn("status", self.last_reply)
        self.assertNotEqual(Task.objects.get().status.category, "done")

    def test_an_archived_project_refuses(self):
        self.post(self.url("archive/"))
        self.command("create APL x")
        self.assertIn("archived", self.last_reply.lower())

    def test_validation_errors_are_explained(self):
        self.command("create APL " + "x" * 300)
        self.assertEqual(Task.objects.count(), 0)
        self.assertIn("too long", self.last_reply)

    def test_replaying_the_same_trigger_creates_one_task(self):
        for _ in range(3):
            self.command("create APL Once only", trigger="same")
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(len(self.hub.replies), 1)
        self.assertEqual(InboundWebhook.objects.get().status, "processed")

    def test_replies_only_go_to_slack_hosts(self):
        self.command("create APL x", hook="https://evil.example.com/steal")
        self.assertEqual(self.hub.replies, [])
        self.assertEqual(Task.objects.count(), 1)  # the command itself still ran

    def test_an_unexpected_crash_gives_a_polite_reply(self):
        from unittest import mock

        with mock.patch(
            "integrations.slack.commands.task_service.create",
            side_effect=RuntimeError("boom"),
        ):
            self.command("create APL x")
        self.assertIn("something went wrong", self.last_reply)
