from allauth.socialaccount.models import SocialAccount
from django.core.cache import cache
from rest_framework.test import APIClient

from accounts.services import google_service
from accounts.tests.base import PASSWORD, ApiTestCase
from projects.models import Membership, Project

PROJECT_BODY = {"name": "Apollo", "task_key": "apl"}


class FakeVerifier(google_service.GoogleTokenVerifier):
    def __init__(self, sub: str, email: str, verified: bool = True):
        self.profile = google_service.GoogleProfile(
            sub=sub,
            email=email,
            email_verified=verified,
            first_name="G",
            last_name="User",
            name="G User",
            picture="",
            raw={},
        )

    def verify(self, token: str) -> google_service.GoogleProfile:
        return self.profile


class ProjectTestCase(ApiTestCase):
    def setUp(self) -> None:
        super().setUp()
        cache.clear()
        self.owner = self.make_user("owner@example.com", display_name="Olive")
        self.bob = self.make_user(
            "bob@example.com", first_name="Bob", display_name="Bob"
        )
        self.login("owner@example.com")

    def switch(self, email: str, password: str = PASSWORD) -> None:
        """Log in as another user in a fresh browser session."""
        self.client = APIClient(enforce_csrf_checks=True, HTTP_USER_AGENT="Firefox")
        self.client.get("/api/csrf/")
        response = self.login(email, password)
        assert response.status_code == 200, response.content

    def put(self, path: str, data: dict | None = None):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.put(path, data or {}, format="json", **self._headers())

    def get(self, path: str):
        return self.client.get(path)

    def create_project(self, **extra) -> dict:
        response = self.post("/api/projects/", {**PROJECT_BODY, **extra})
        assert response.status_code == 201, response.content
        return response.json()["data"]

    def join(self, project: dict, email: str = "bob@example.com") -> dict:
        """`email` asks to join with the project's code; returns the request."""
        self.switch(email)
        response = self.post("/api/projects/join/", {"code": project["join_code"]})
        assert response.status_code == 201, response.content
        return response.json()["data"]

    def approve(
        self,
        project: dict,
        join_request: dict,
        owner_email: str,
        body: dict | None = None,
    ):
        self.switch(owner_email)
        url = (
            f"/api/projects/{project['id']}/join-requests/{join_request['id']}/approve/"
        )
        return self.post(url, body)

    def add_member(
        self,
        project: dict,
        email: str = "bob@example.com",
        preset: str | None = "contributor",
    ) -> None:
        """Join and get approved. Members start with the Contributor preset so
        most tests can focus on their own subject; pass `preset=None` for a
        member with no permissions at all."""
        request = self.join(project, email)
        body = {"preset": preset} if preset else None
        response = self.approve(project, request, "owner@example.com", body)
        assert response.status_code == 200, response.content

    def link_google(self, user, sub: str = "g-1") -> None:
        SocialAccount.objects.create(user=user, provider="google", uid=sub)

    def membership(self, project: dict, user) -> Membership:
        return Membership.objects.get(project_id=project["id"], user=user)

    def project_row(self, project: dict) -> Project:
        return Project.all_objects.get(pk=project["id"])
