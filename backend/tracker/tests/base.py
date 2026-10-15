from projects.tests.base import ProjectTestCase


class TrackerTestCase(ProjectTestCase):
    """Owner (logged in) with a project, plus Bob as a plain member."""

    def setUp(self) -> None:
        super().setUp()
        self.project = self.create_project()
        self.pid = self.project["id"]
        self.add_member(self.project)
        self.switch("owner@example.com")

    # URL helpers
    def url(self, path: str = "") -> str:
        return f"/api/projects/{self.pid}/{path}"

    def items(self, path: str, **params) -> list[dict]:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        response = self.get(self.url(path) + (f"?{query}" if query else ""))
        assert response.status_code == 200, response.content
        return response.json()["data"]["items"]

    def create_task(self, title: str = "Write docs", **extra) -> dict:
        response = self.post(self.url("tasks/"), {"title": title, **extra})
        assert response.status_code == 201, response.content
        return response.json()["data"]

    def status_id(self, name: str) -> str:
        return next(s["id"] for s in self.items("statuses/") if s["name"] == name)

    def priority_id(self, name: str) -> str:
        return next(p["id"] for p in self.items("priorities/") if p["name"] == name)

    def user_id(self, email: str) -> str:
        from accounts.models import User

        return str(User.objects.get(email=email).pk)
