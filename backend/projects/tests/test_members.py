from datetime import timedelta
from unittest import mock

from django.core import mail
from django.utils import timezone

from projects.models import JoinRequest, Membership, OwnershipTransfer
from projects.services.reassignment import ReassignmentRegistry, registry
from projects.tasks import expire_join_requests, expire_transfers
from projects.tests.base import PASSWORD, ProjectTestCase


class JoinTests(ProjectTestCase):
    def test_join_flow(self):
        project = self.create_project()
        request = self.join(project)
        self.assertEqual(request["status"], "pending")
        self.assertEqual(request["project"], {"name": "Apollo", "description": ""})
        self.assertTrue(any("owner@example.com" in m.to for m in mail.outbox))

        # Not a member yet.
        self.assertEqual(self.get(f"/api/projects/{project['id']}/").status_code, 404)

        self.switch("owner@example.com")
        listing = self.get(f"/api/projects/{project['id']}/join-requests/").json()
        item = listing["data"]["items"][0]
        self.assertEqual(item["user"]["email"], "bob@example.com")

        approved = self.approve(project, request, "owner@example.com")
        self.assertEqual(approved.json()["data"]["status"], "approved")

        self.switch("bob@example.com")
        detail = self.get(f"/api/projects/{project['id']}/").json()["data"]
        self.assertEqual(detail["role"], "member")
        self.assertEqual(detail["member_count"], 2)

    def test_code_is_case_insensitive(self):
        project = self.create_project()
        self.switch("bob@example.com")
        response = self.post(
            "/api/projects/join/", {"code": f" {project['join_code'].lower()} "}
        )
        self.assertEqual(response.status_code, 201)

    def test_wrong_codes_throttle_per_user(self):
        self.switch("bob@example.com")
        for _ in range(5):
            response = self.post("/api/projects/join/", {"code": "ZZZZZZ"})
            self.assertEqual(response.json()["code"], "invalid_join_code")
        again = self.post("/api/projects/join/", {"code": "ZZZZZZ"})
        self.assertEqual(again.status_code, 429)
        self.assertEqual(again.json()["code"], "join_code_throttled")

    def test_duplicate_and_member_cases(self):
        project = self.create_project()
        self.switch("bob@example.com")
        self.post("/api/projects/join/", {"code": project["join_code"]})
        dup = self.post("/api/projects/join/", {"code": project["join_code"]})
        self.assertEqual(dup.json()["code"], "join_request_pending")
        self.switch("owner@example.com")
        own = self.post("/api/projects/join/", {"code": project["join_code"]})
        self.assertEqual(own.json()["code"], "already_member")

    def test_open_request_cap(self):
        codes = []
        for i in range(11):
            codes.append(self.create_project(name=f"P{i}")["join_code"])
        self.switch("bob@example.com")
        for code in codes[:10]:
            self.assertEqual(
                self.post("/api/projects/join/", {"code": code}).status_code, 201
            )
        last = self.post("/api/projects/join/", {"code": codes[10]})
        self.assertEqual(last.json()["code"], "too_many_open_requests")

    def test_reject_then_cooldown_then_retry(self):
        project = self.create_project()
        request = self.join(project)
        self.switch("owner@example.com")
        url = f"/api/projects/{project['id']}/join-requests/{request['id']}/reject/"
        self.assertEqual(self.post(url).status_code, 200)
        self.assertEqual(self.post(url).json()["code"], "join_request_not_pending")

        self.switch("bob@example.com")
        retry = self.post("/api/projects/join/", {"code": project["join_code"]})
        self.assertEqual(retry.json()["code"], "join_request_cooldown")
        JoinRequest.objects.update(decided_at=timezone.now() - timedelta(hours=25))
        retry = self.post("/api/projects/join/", {"code": project["join_code"]})
        self.assertEqual(retry.status_code, 201)

    def test_member_cannot_review_requests(self):
        project = self.create_project()
        self.add_member(project)
        self.make_user("carl@example.com")
        request = self.join(project, "carl@example.com")
        self.switch("bob@example.com")
        base = f"/api/projects/{project['id']}/join-requests/"
        self.assertEqual(self.get(base).status_code, 403)
        self.assertEqual(self.post(f"{base}{request['id']}/approve/").status_code, 403)

    def test_expiry(self):
        project = self.create_project()
        request = self.join(project)
        JoinRequest.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
        self.switch("owner@example.com")
        late = self.post(
            f"/api/projects/{project['id']}/join-requests/{request['id']}/approve/"
        )
        self.assertEqual(late.json()["code"], "join_request_expired")
        self.assertFalse(Membership.objects.filter(user=self.bob).exists())
        JoinRequest.objects.update(status="pending")
        self.assertEqual(expire_join_requests.delay().get(), 1)

    def test_archived_project_rejects_joins(self):
        project = self.create_project()
        self.post(f"/api/projects/{project['id']}/archive/")
        self.switch("bob@example.com")
        response = self.post("/api/projects/join/", {"code": project["join_code"]})
        self.assertEqual(response.json()["code"], "project_archived")


class RemoveAndLeaveTests(ProjectTestCase):
    def test_remove_member_runs_reassignment(self):
        project = self.create_project()
        self.add_member(project)
        self.make_user("carl@example.com")
        self.add_member(project, "carl@example.com")
        self.switch("owner@example.com")
        carl = self.make_user("dave@example.com")  # not a member

        calls = []
        local = ReassignmentRegistry()
        local.register("tasks", lambda p, leaving, to: calls.append((leaving, to)))
        with mock.patch("projects.services.membership_service.registry", local):
            url = f"/api/projects/{project['id']}/members/{self.bob.pk}/"
            carl_member = Membership.objects.get(user__email="carl@example.com").user
            bad = self.client.delete(
                url,
                {"reassign": {"tasks": str(carl.pk)}},
                format="json",
                **self._headers(),
            )
            self.assertEqual(bad.json()["code"], "invalid_reassignment")
            unknown = self.client.delete(
                url,
                {"reassign": {"nope": str(carl_member.pk)}},
                format="json",
                **self._headers(),
            )
            self.assertEqual(unknown.json()["code"], "invalid_reassignment")
            self.assertEqual(calls, [])
            ok = self.client.delete(
                url,
                {"reassign": {"tasks": str(carl_member.pk)}},
                format="json",
                **self._headers(),
            )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(calls, [(self.bob, carl_member)])
        self.assertFalse(Membership.objects.filter(user=self.bob).exists())
        self.assertTrue(any("bob@example.com" in m.to for m in mail.outbox))

    def test_unmapped_items_become_unassigned(self):
        project = self.create_project()
        self.add_member(project)
        self.switch("owner@example.com")
        calls = []
        local = ReassignmentRegistry()
        local.register("notes", lambda p, leaving, to: calls.append(to))
        with mock.patch("projects.services.membership_service.registry", local):
            self.delete(f"/api/projects/{project['id']}/members/{self.bob.pk}/")
        self.assertEqual(calls, [None])

    def test_owner_cannot_be_removed_and_members_cannot_remove(self):
        project = self.create_project()
        self.add_member(project)
        self.switch("owner@example.com")
        own = self.delete(f"/api/projects/{project['id']}/members/{self.owner.pk}/")
        self.assertEqual(own.json()["code"], "cannot_remove_owner")
        self.switch("bob@example.com")
        denied = self.delete(f"/api/projects/{project['id']}/members/{self.owner.pk}/")
        self.assertEqual(denied.status_code, 403)

    def test_member_list_hides_emails_from_members(self):
        project = self.create_project()
        self.add_member(project)
        base = f"/api/projects/{project['id']}/members/"
        as_member = (
            self.switch("bob@example.com") or self.get(base).json()["data"]["items"]
        )
        self.assertNotIn("email", as_member[0])
        self.assertTrue(as_member[0]["is_owner"])
        self.switch("owner@example.com")
        as_owner = self.get(base).json()["data"]["items"]
        self.assertEqual(as_owner[1]["email"], "bob@example.com")

    def test_leave(self):
        project = self.create_project()
        self.add_member(project)
        self.switch("bob@example.com")
        self.assertEqual(
            self.post(f"/api/projects/{project['id']}/leave/").status_code, 200
        )
        self.assertEqual(self.get(f"/api/projects/{project['id']}/").status_code, 404)
        self.switch("owner@example.com")
        owner_leave = self.post(f"/api/projects/{project['id']}/leave/")
        self.assertEqual(owner_leave.json()["code"], "owner_cannot_leave")

    def test_features_register_their_reassignment_handlers(self):
        self.assertEqual(registry.names(), ["notes", "tasks"])


class TransferTests(ProjectTestCase):
    def start(self, project, to_user, **body):
        return self.post(
            f"/api/projects/{project['id']}/transfer/",
            {"to_user": str(to_user.pk), **body},
        )

    def test_transfer_flow(self):
        project = self.create_project()
        self.add_member(project)
        self.switch("owner@example.com")
        self.assertEqual(self.start(project, self.bob).status_code, 400)  # no reauth
        started = self.start(project, self.bob, password=PASSWORD)
        self.assertEqual(started.status_code, 201)
        again = self.start(project, self.bob, password=PASSWORD)
        self.assertEqual(again.json()["code"], "transfer_pending")
        detail = self.get(f"/api/projects/{project['id']}/").json()["data"]
        self.assertEqual(detail["pending_transfer"]["id"], started.json()["data"]["id"])

        self.switch("bob@example.com")
        incoming = self.get("/api/transfers/").json()["data"]["items"]
        self.assertEqual(incoming[0]["project"]["name"], "Apollo")
        accepted = self.post(f"/api/transfers/{incoming[0]['id']}/accept/")
        self.assertEqual(accepted.status_code, 200)

        row = self.project_row(project)
        self.assertEqual(row.owner, self.bob)
        self.assertTrue(self.membership(project, self.bob).is_owner)
        self.assertFalse(self.membership(project, self.owner).is_owner)
        self.assertEqual(
            self.get(f"/api/projects/{project['id']}/").json()["data"]["role"], "owner"
        )
        self.switch("owner@example.com")
        old = self.get(f"/api/projects/{project['id']}/").json()["data"]
        self.assertEqual(old["role"], "member")
        self.assertNotIn("member.remove", old["permissions"])

    def test_only_target_can_accept(self):
        project = self.create_project()
        self.add_member(project)
        self.make_user("carl@example.com")
        self.add_member(project, "carl@example.com")
        self.switch("owner@example.com")
        transfer_id = self.start(project, self.bob, password=PASSWORD).json()["data"][
            "id"
        ]
        self.switch("carl@example.com")
        self.assertEqual(
            self.post(f"/api/transfers/{transfer_id}/accept/").status_code, 404
        )

    def test_target_must_be_other_member(self):
        project = self.create_project()
        outsider = self.make_user("eve@example.com")
        self.assertEqual(
            self.start(project, outsider, password=PASSWORD).status_code, 409
        )
        self.assertEqual(
            self.start(project, self.owner, password=PASSWORD).status_code, 409
        )

    def test_cancel_and_expire(self):
        project = self.create_project()
        self.add_member(project)
        self.switch("owner@example.com")
        self.start(project, self.bob, password=PASSWORD)
        cancel = self.post(f"/api/projects/{project['id']}/transfer/cancel/")
        self.assertEqual(cancel.json()["data"]["status"], "cancelled")
        self.assertEqual(
            self.post(f"/api/projects/{project['id']}/transfer/cancel/").status_code,
            404,
        )

        transfer_id = self.start(project, self.bob, password=PASSWORD).json()["data"][
            "id"
        ]
        OwnershipTransfer.objects.filter(pk=transfer_id).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.switch("bob@example.com")
        late = self.post(f"/api/transfers/{transfer_id}/accept/")
        self.assertEqual(late.json()["code"], "transfer_expired")
        self.assertEqual(self.project_row(project).owner, self.owner)
        OwnershipTransfer.objects.filter(pk=transfer_id).update(status="pending")
        self.assertEqual(expire_transfers.delay().get(), 1)

    def test_member_cannot_start_transfer(self):
        project = self.create_project()
        self.add_member(project)
        self.switch("bob@example.com")
        response = self.start(project, self.owner, password=PASSWORD)
        self.assertEqual(response.status_code, 403)
