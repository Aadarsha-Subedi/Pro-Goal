from accounts.models import User
from projects.constants import permissions as codes
from projects.models import ActivityLog, MemberPermission
from projects.tests.base import ProjectTestCase


class GrantTestCase(ProjectTestCase):
    """Owner (logged in) with a project; Bob and Carl are members with NO grants."""

    def setUp(self) -> None:
        super().setUp()
        self.carl = self.make_user(
            "carl@example.com", first_name="Carl", display_name="Carl"
        )
        self.project = self.create_project()
        self.pid = self.project["id"]
        self.add_member(self.project, "bob@example.com", preset=None)
        self.add_member(self.project, "carl@example.com", preset=None)
        self.switch("owner@example.com")

    def uid(self, email: str) -> str:
        return str(User.objects.get(email=email).pk)

    def url(self, path: str = "") -> str:
        return f"/api/projects/{self.pid}/{path}"

    def grants_url(self, email: str) -> str:
        return self.url(f"members/{self.uid(email)}/permissions/")

    def grant(self, email: str, permissions=None, preset=None):
        body = {"preset": preset} if preset else {"permissions": permissions or []}
        return self.put(self.grants_url(email), body)

    def held(self, email: str) -> list[str]:
        return self.get(self.grants_url(email)).json()["data"]["permissions"]


class RegistryTests(GrantTestCase):
    def test_registry_endpoint(self):
        data = self.get("/api/permissions/").json()["data"]
        by_code = {p["code"]: p for p in data["permissions"]}
        self.assertEqual(set(by_code), set(codes.ALL_PERMISSIONS))
        self.assertTrue(
            all(
                p["label"] and p["description"] and p["group"] in data["groups"]
                for p in data["permissions"]
            )
        )
        self.assertEqual(
            {p["name"] for p in data["presets"]}, {"viewer", "contributor", "manager"}
        )
        self.assertIn("Transfer ownership", data["owner_only"])

    def test_requires_login(self):
        self.client.get("/api/csrf/")
        from rest_framework.test import APIClient

        anonymous = APIClient()
        self.assertEqual(anonymous.get("/api/permissions/").status_code, 401)

    def test_presets_only_contain_registered_codes(self):
        for preset in codes.PRESETS.values():
            self.assertLessEqual(preset.codes, codes.REGISTERED)
        self.assertEqual(codes.PRESETS["viewer"].codes, frozenset())
        self.assertNotIn(codes.PERMISSIONS_MANAGE, codes.PRESETS["manager"].codes)
        self.assertNotIn(codes.TASK_DELETE, codes.PRESETS["contributor"].codes)

    def test_every_code_used_by_a_service_is_registered(self):
        import pathlib
        import re

        root = pathlib.Path(__file__).resolve().parents[2]
        used = set()
        for app in ("projects", "tracker", "attachments"):
            for path in (root / app / "services").glob("*.py"):
                used |= set(re.findall(r"codes\.([A-Z_]+)\b", path.read_text()))
        values = {getattr(codes, name) for name in used if hasattr(codes, name)}
        self.assertTrue(values)
        self.assertLessEqual(values, codes.REGISTERED)


class NoGrantsTests(GrantTestCase):
    def test_member_without_grants_can_read_but_not_write(self):
        self.switch("owner@example.com")
        task = self.post(self.url("tasks/"), {"title": "t"}).json()["data"]
        self.switch("bob@example.com")
        self.assertEqual(self.get(self.url()).status_code, 200)
        self.assertEqual(self.get(self.url("tasks/")).status_code, 200)
        self.assertEqual(self.get(self.url("members/")).status_code, 200)
        self.assertEqual(
            self.get(self.url(f"tasks/{task['number']}/")).status_code, 200
        )
        writes = [
            self.post(self.url("tasks/"), {"title": "x"}),
            self.patch(self.url(f"tasks/{task['number']}/"), {"title": "x"}),
            self.delete(self.url(f"tasks/{task['number']}/")),
            self.post(self.url("notes/"), {"title": "n"}),
            self.post(self.url(f"tasks/{task['number']}/comments/"), {"body": "hi"}),
            self.post(self.url("statuses/"), {"name": "X", "category": "todo"}),
            self.post(self.url("priorities/"), {"name": "X"}),
            self.patch(self.url(), {"name": "x"}),
            self.delete(self.url(f"members/{self.uid('carl@example.com')}/")),
            self.get(self.url("join-requests/")),
            self.put(self.grants_url("carl@example.com"), {"permissions": []}),
            self.post(
                self.url("attachments/upload-url/"),
                {
                    "target_type": "task",
                    "target": str(task["number"]),
                    "filename": "a.pdf",
                    "content_type": "application/pdf",
                    "size": 10,
                },
            ),
        ]
        for response in writes:
            self.assertEqual(response.status_code, 403, response.content)

    def test_project_detail_lists_held_codes(self):
        self.switch("bob@example.com")
        self.assertEqual(self.get(self.url()).json()["data"]["permissions"], [])
        self.switch("owner@example.com")
        self.grant("bob@example.com", ["task.create"])
        self.switch("bob@example.com")
        self.assertEqual(
            self.get(self.url()).json()["data"]["permissions"], ["task.create"]
        )
        self.switch("owner@example.com")
        owner = self.get(self.url()).json()["data"]["permissions"]
        self.assertEqual(owner, list(codes.ALL_PERMISSIONS))


class SingleGrantTests(GrantTestCase):
    def test_one_code_unlocks_exactly_that_action(self):
        task = self.post(self.url("tasks/"), {"title": "t"}).json()["data"]
        self.grant("bob@example.com", ["task.title.change"])
        self.switch("bob@example.com")
        url = self.url(f"tasks/{task['number']}/")
        self.assertEqual(self.patch(url, {"title": "new"}).status_code, 200)
        denied = self.patch(url, {"due_date": "2031-01-01"})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["code"], "fields_forbidden")

    def test_whole_request_fails_together_and_lists_every_forbidden_field(self):
        task = self.post(self.url("tasks/"), {"title": "t"}).json()["data"]
        self.grant("bob@example.com", ["task.description.change"])
        self.switch("bob@example.com")
        response = self.patch(
            self.url(f"tasks/{task['number']}/"),
            {"title": "x", "due_date": "2031-01-01", "description": "ok"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            sorted(e["field"] for e in response.json()["errors"]), ["due_date", "title"]
        )
        detail = self.get(self.url(f"tasks/{task['number']}/")).json()["data"]
        self.assertEqual((detail["title"], detail["description"]), ("t", ""))

    def test_status_member_and_attachment_codes(self):
        self.grant(
            "bob@example.com",
            ["status.create", "member.remove", "member.approve", "comment.moderate"],
        )
        self.switch("bob@example.com")
        self.assertEqual(
            self.post(
                self.url("statuses/"), {"name": "QA", "category": "in_progress"}
            ).status_code,
            201,
        )
        self.assertEqual(self.get(self.url("join-requests/")).status_code, 200)
        removed = self.delete(self.url(f"members/{self.uid('carl@example.com')}/"))
        self.assertEqual(removed.status_code, 200)
        # status.update was not granted.
        status_id = self.get(self.url("statuses/")).json()["data"]["items"][0]["id"]
        self.assertEqual(
            self.patch(self.url(f"statuses/{status_id}/"), {"name": "z"}).status_code,
            403,
        )

    def test_revoke_takes_effect_on_the_next_request(self):
        self.grant("bob@example.com", ["task.create"])
        self.switch("bob@example.com")
        self.assertEqual(self.post(self.url("tasks/"), {"title": "a"}).status_code, 201)
        self.switch("owner@example.com")
        self.grant("bob@example.com", [])
        self.switch("bob@example.com")
        self.assertEqual(self.post(self.url("tasks/"), {"title": "b"}).status_code, 403)

    def test_own_comments_and_attachments_need_no_grant(self):
        task = self.post(self.url("tasks/"), {"title": "t"}).json()["data"]
        self.grant("bob@example.com", ["comment.create"])
        self.switch("bob@example.com")
        comment = self.post(
            self.url(f"tasks/{task['number']}/comments/"), {"body": "mine"}
        ).json()["data"]
        edited = self.patch(
            self.url(f"tasks/{task['number']}/comments/{comment['id']}/"),
            {"body": "edit"},
        )
        self.assertEqual(edited.status_code, 200)
        removed = self.delete(
            self.url(f"tasks/{task['number']}/comments/{comment['id']}/")
        )
        self.assertEqual(removed.status_code, 200)

    def test_leaving_needs_no_grant(self):
        self.switch("bob@example.com")
        self.assertEqual(self.post(self.url("leave/")).status_code, 200)


class ReplaceGrantsTests(GrantTestCase):
    def test_replace_diff_and_activity_log(self):
        first = self.grant("bob@example.com", ["task.create", "note.create"])
        self.assertEqual(
            first.json()["data"]["permissions"], ["task.create", "note.create"]
        )
        second = self.grant("bob@example.com", ["note.create", "comment.create"])
        self.assertEqual(
            sorted(second.json()["data"]["permissions"]),
            ["comment.create", "note.create"],
        )
        log = ActivityLog.objects.filter(action="member.permissions_changed").first()
        self.assertEqual(
            log.changes, {"added": ["comment.create"], "removed": ["task.create"]}
        )
        # Unchanged request logs nothing new.
        count = ActivityLog.objects.filter(action="member.permissions_changed").count()
        self.grant("bob@example.com", ["note.create", "comment.create"])
        self.assertEqual(
            ActivityLog.objects.filter(action="member.permissions_changed").count(),
            count,
        )

    def test_presets_and_matching(self):
        response = self.grant("bob@example.com", preset="contributor")
        self.assertEqual(response.json()["data"]["preset"], "contributor")
        self.assertEqual(
            set(self.held("bob@example.com")), set(codes.PRESETS["contributor"].codes)
        )
        self.assertEqual(
            self.grant("bob@example.com", preset="viewer").json()["data"]["preset"],
            "viewer",
        )
        custom = self.grant("bob@example.com", ["task.create"])
        self.assertIsNone(custom.json()["data"]["preset"])

    def test_validation(self):
        unknown = self.grant("bob@example.com", ["task.fly"])
        self.assertEqual(unknown.json()["code"], "unknown_permission")
        bad_preset = self.grant("bob@example.com", preset="boss")
        self.assertEqual(bad_preset.json()["code"], "unknown_preset")
        both = self.put(
            self.grants_url("bob@example.com"), {"preset": "viewer", "permissions": []}
        )
        self.assertEqual(both.status_code, 400)
        neither = self.put(self.grants_url("bob@example.com"), {})
        self.assertEqual(neither.status_code, 400)

    def test_owner_cannot_be_targeted_and_unknown_member_is_404(self):
        owner = self.put(self.grants_url("owner@example.com"), {"permissions": []})
        self.assertEqual(owner.status_code, 409)
        self.assertEqual(owner.json()["code"], "cannot_manage_owner")
        stranger = self.make_user("eve@example.com")
        url = self.url(f"members/{stranger.pk}/permissions/")
        self.assertEqual(self.put(url, {"permissions": []}).status_code, 404)

    def test_archived_project_blocks_changes(self):
        self.post(self.url("archive/"))
        self.assertEqual(
            self.grant("bob@example.com", ["task.create"]).json()["code"],
            "project_archived",
        )

    def test_removed_member_loses_grants(self):
        self.grant("bob@example.com", ["task.create"])
        bob = self.uid("bob@example.com")
        self.delete(self.url(f"members/{bob}/"))
        self.assertFalse(
            MemberPermission.objects.filter(membership__user_id=bob).exists()
        )


class DelegationTests(GrantTestCase):
    def setUp(self) -> None:
        super().setUp()
        # Bob manages permissions and holds task.create only.
        self.grant("bob@example.com", ["permissions.manage", "task.create"])
        self.switch("bob@example.com")

    def test_manager_can_hand_out_what_they_hold(self):
        response = self.grant("carl@example.com", ["task.create"])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.held("carl@example.com"), ["task.create"])

    def test_manager_cannot_grant_what_they_lack(self):
        response = self.grant("carl@example.com", ["task.create", "member.remove"])
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "cannot_grant_permission")
        self.assertEqual(
            [e["code"] for e in response.json()["errors"]], ["member.remove"]
        )
        self.assertEqual(self.held("carl@example.com"), [])

    def test_manager_cannot_revoke_what_they_lack(self):
        self.switch("owner@example.com")
        self.grant("carl@example.com", ["task.create", "member.remove"])
        self.switch("bob@example.com")
        response = self.grant("carl@example.com", ["task.create"])
        self.assertEqual(response.json()["code"], "cannot_grant_permission")
        self.assertEqual(
            sorted(self.held("carl@example.com")), ["member.remove", "task.create"]
        )

    def test_manager_cannot_use_a_preset_bigger_than_their_own_grants(self):
        self.assertEqual(
            self.grant("carl@example.com", preset="contributor").status_code, 403
        )

    def test_manager_cannot_touch_the_owner(self):
        response = self.put(self.grants_url("owner@example.com"), {"permissions": []})
        self.assertEqual(response.json()["code"], "cannot_manage_owner")

    def test_self_revoke_allowed_self_escalation_not(self):
        escalate = self.grant(
            "bob@example.com", ["permissions.manage", "task.create", "member.remove"]
        )
        self.assertEqual(escalate.status_code, 403)
        revoke = self.grant("bob@example.com", ["task.create"])
        self.assertEqual(revoke.status_code, 200)
        # permissions.manage is gone, so the next change is refused.
        self.assertEqual(self.grant("carl@example.com", []).status_code, 403)

    def test_who_can_read_grants(self):
        self.assertEqual(
            self.get(self.grants_url("carl@example.com")).status_code, 200
        )  # manager
        self.switch("carl@example.com")
        self.assertEqual(
            self.get(self.grants_url("carl@example.com")).status_code, 200
        )  # self
        self.assertEqual(
            self.get(self.grants_url("bob@example.com")).status_code, 403
        )  # other member
        self.switch("owner@example.com")
        self.assertEqual(self.get(self.grants_url("bob@example.com")).status_code, 200)

    def test_non_member_gets_404(self):
        self.make_user("eve@example.com")
        self.switch("eve@example.com")
        self.assertEqual(self.get(self.grants_url("bob@example.com")).status_code, 404)


class ApprovalTests(GrantTestCase):
    def pending(self, email: str) -> dict:
        self.make_user(email)
        return self.join(self.project, email)

    def test_approve_with_preset_and_with_explicit_codes(self):
        first = self.pending("dave@example.com")
        response = self.approve(
            self.project, first, "owner@example.com", {"preset": "contributor"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(self.held("dave@example.com")), set(codes.PRESETS["contributor"].codes)
        )

        second = self.pending("erin@example.com")
        self.approve(
            self.project, second, "owner@example.com", {"permissions": ["note.create"]}
        )
        self.assertEqual(self.held("erin@example.com"), ["note.create"])

    def test_default_is_no_permissions(self):
        pending = self.pending("dave@example.com")
        self.approve(self.project, pending, "owner@example.com")
        self.assertEqual(self.held("dave@example.com"), [])

    def test_approver_without_manage_cannot_give_permissions(self):
        self.switch("owner@example.com")
        self.grant("bob@example.com", ["member.approve"])
        pending = self.pending("dave@example.com")
        refused = self.approve(
            self.project, pending, "bob@example.com", {"preset": "contributor"}
        )
        self.assertEqual(refused.status_code, 403)
        # Nothing was applied: the request is still pending and approvable.
        listing = self.get(self.url("join-requests/")).json()["data"]["items"]
        self.assertEqual([r["status"] for r in listing], ["pending"])
        plain = self.approve(self.project, pending, "bob@example.com")
        self.assertEqual(plain.status_code, 200)

    def test_approver_with_manage_is_limited_to_what_they_hold(self):
        self.switch("owner@example.com")
        self.grant(
            "bob@example.com", ["member.approve", "permissions.manage", "note.create"]
        )
        pending = self.pending("dave@example.com")
        too_much = self.approve(
            self.project,
            pending,
            "bob@example.com",
            {"permissions": ["note.create", "task.create"]},
        )
        self.assertEqual(too_much.json()["code"], "cannot_grant_permission")
        fine = self.approve(
            self.project, pending, "bob@example.com", {"permissions": ["note.create"]}
        )
        self.assertEqual(fine.status_code, 200)


class TransferTests(GrantTestCase):
    def test_transfer_clears_both_owners_grants(self):
        self.grant("bob@example.com", ["task.create", "note.create"])
        started = self.post(
            self.url("transfer/"),
            {"to_user": self.uid("bob@example.com"), "password": "Correct-Horse-9"},
        )
        self.assertEqual(started.status_code, 201)
        self.switch("bob@example.com")
        self.post(f"/api/transfers/{started.json()['data']['id']}/accept/")
        self.assertFalse(
            MemberPermission.objects.filter(
                membership__project_id=self.pid,
                membership__user__email__in=["bob@example.com", "owner@example.com"],
            ).exists()
        )
        detail = self.get(self.url()).json()["data"]
        self.assertEqual(detail["role"], "owner")
        self.assertEqual(detail["permissions"], list(codes.ALL_PERMISSIONS))
        self.switch("owner@example.com")
        old = self.get(self.url()).json()["data"]
        self.assertEqual((old["role"], old["permissions"]), ("member", []))


class BackfillTests(GrantTestCase):
    def test_backfill_gives_contributor_to_existing_non_owner_members(self):
        import importlib

        from django.apps import apps

        migration = importlib.import_module(
            "projects.migrations.0003_backfill_contributor_grants"
        )
        MemberPermission.objects.all().delete()
        migration.backfill(apps, None)
        self.assertEqual(
            set(self.held("bob@example.com")), set(codes.PRESETS["contributor"].codes)
        )
        self.assertEqual(
            set(migration.CONTRIBUTOR), set(codes.PRESETS["contributor"].codes)
        )
        self.assertFalse(
            MemberPermission.objects.filter(
                membership__user__email="owner@example.com"
            ).exists()
        )
        # Running it twice adds nothing.
        before = MemberPermission.objects.count()
        migration.backfill(apps, None)
        self.assertEqual(MemberPermission.objects.count(), before)
