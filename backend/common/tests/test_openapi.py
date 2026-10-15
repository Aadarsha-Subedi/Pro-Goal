import tempfile
from pathlib import Path

import yaml
from django.core.management import call_command
from django.test import SimpleTestCase
from rest_framework.test import APIClient

from common.openapi import declared_serializers

SCHEMA_FILE = Path(__file__).resolve().parents[2] / "docs" / "openapi.yml"
UNSAFE = ("post", "put", "patch", "delete")


def build_schema() -> dict:
    with tempfile.NamedTemporaryFile(suffix=".yml") as handle:
        call_command(
            "spectacular", "--file", handle.name, "--validate", "--fail-on-warn"
        )
        return yaml.safe_load(Path(handle.name).read_text())


class OpenApiTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.schema = build_schema()

    def operations(self):
        for path, item in self.schema["paths"].items():
            for method, operation in item.items():
                if method in ("get", "post", "put", "patch", "delete"):
                    yield path, method, operation

    def test_builds_without_warnings_and_only_describes_the_api(self):
        self.assertTrue(self.schema["paths"])
        self.assertTrue(all(path.startswith("/api/") for path in self.schema["paths"]))
        self.assertFalse(
            [p for p in self.schema["paths"] if "/admin" in p or "schema" in p]
        )

    def test_every_drf_route_is_documented(self):
        from django.urls import get_resolver
        from rest_framework.views import APIView

        def walk(patterns, prefix=""):
            for pattern in patterns:
                route = prefix + str(pattern.pattern)
                if hasattr(pattern, "url_patterns"):
                    yield from walk(pattern.url_patterns, route)
                else:
                    view = getattr(pattern.callback, "cls", None)
                    if isinstance(view, type) and issubclass(view, APIView):
                        yield route, view

        import re

        documented = set(self.schema["paths"])
        missing = []
        for route, _view in walk(get_resolver().url_patterns):
            if not route.startswith("api/") or route.startswith(
                ("api/schema", "api/docs")
            ):
                continue
            template = "/" + re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", route)
            if template not in documented:
                missing.append(template)
        self.assertEqual(missing, [])

    def test_request_bodies_match_what_the_views_parse(self):
        checked = 0
        for path, method, operation in self.operations():
            if method == "get" or method == "delete":
                continue
            view = self._view_for(path)
            if view is None:
                continue
            body, _ = declared_serializers(view, method)
            has_body = "requestBody" in operation
            self.assertEqual(has_body, body is not None, f"{method.upper()} {path}")
            checked += body is not None
        self.assertGreater(checked, 30)

    def _view_for(self, path: str):
        import re

        from django.urls import Resolver404, resolve

        concrete = re.sub(
            r"\{(\w+)\}",
            lambda m: (
                "1"
                if m.group(1) in ("number",)
                else "00000000-0000-0000-0000-000000000000"
            ),
            path,
        )
        try:
            return resolve(concrete).func.cls
        except Resolver404, AttributeError:
            return None

    def test_every_response_uses_the_envelope(self):
        for path, method, operation in self.operations():
            ok = operation["responses"].get("200")
            self.assertIsNotNone(ok, f"{method} {path}")
            ref = ok["content"]["application/json"]["schema"]["$ref"]
            self.assertTrue(ref.endswith("/Envelope"), f"{method} {path}")
            errors = [k for k in operation["responses"] if k.startswith(("4", "5"))]
            self.assertIn(
                "400", errors
            ) if method != "get" and "requestBody" in operation else None

    def test_authentication_and_csrf_are_described(self):
        schema = self.schema["paths"]
        login = schema["/api/auth/login/"]["post"]
        self.assertFalse(login.get("security"))  # public
        self.assertIn("X-CSRFToken", [p["name"] for p in login["parameters"]])
        tasks = schema["/api/projects/{project_id}/tasks/"]
        self.assertEqual(tasks["get"]["security"], [{"sessionAuth": []}])
        self.assertNotIn("X-CSRFToken", [p["name"] for p in tasks["get"]["parameters"]])
        self.assertIn("X-CSRFToken", [p["name"] for p in tasks["post"]["parameters"]])
        # Provider callbacks have neither a session nor CSRF.
        hook = schema["/api/integrations/{provider}/webhook/"]["post"]
        self.assertFalse(hook.get("security"))
        self.assertNotIn("X-CSRFToken", [p["name"] for p in hook.get("parameters", [])])
        self.assertEqual(hook["tags"], ["provider callbacks"])
        self.assertIn("sessionAuth", self.schema["components"]["securitySchemes"])

    def test_query_parameters_and_pagination_are_documented(self):
        def names(path, method="get"):
            return {
                p["name"]
                for p in self.schema["paths"][path][method].get("parameters", [])
            }

        self.assertTrue(
            {"status", "priority", "assignee", "overdue", "ordering", "limit", "offset"}
            <= names("/api/projects/{project_id}/tasks/")
        )
        self.assertTrue(
            {"q", "tag", "starts_after", "ends_before", "limit", "offset"}
            <= names("/api/explore/")
        )
        self.assertTrue(
            {"actor", "action", "created_after", "limit"}
            <= names("/api/projects/{project_id}/activity/")
        )
        self.assertTrue(
            {"event_type", "limit", "offset"} <= names("/api/me/security-events/")
        )

    def test_operations_are_tagged_and_ids_are_unique(self):
        ids = [op["operationId"] for _p, _m, op in self.operations()]
        self.assertEqual(len(ids), len(set(ids)))
        tags = {t for _p, _m, op in self.operations() for t in op["tags"]}
        self.assertTrue(
            {
                "auth",
                "me",
                "projects",
                "tasks",
                "notes",
                "attachments",
                "activity",
                "explore",
                "integrations",
            }
            <= tags
        )
        self.assertTrue(all(op["tags"] for _p, _m, op in self.operations()))

    def test_the_checked_in_schema_is_current(self):
        self.assertTrue(
            SCHEMA_FILE.exists(), "run: manage.py spectacular --file docs/openapi.yml"
        )
        self.assertEqual(
            yaml.safe_load(SCHEMA_FILE.read_text()),
            self.schema,
            "docs/openapi.yml is out of date. Run: uv run python manage.py spectacular --file docs/openapi.yml",
        )

    def test_docs_routes_exist_only_in_debug(self):
        # config/urls.py adds them under `if settings.DEBUG`; tests run with DEBUG off.
        self.assertEqual(APIClient().get("/api/schema/").status_code, 404)
        self.assertEqual(APIClient().get("/api/docs/").status_code, 404)
