"""OpenAPI generation (drf-spectacular) adapted to how this API is written.

Views parse their input with `SomeSerializer.parse(request.data)` and answer
with the shared response envelope, so the stock schema generator cannot see
either. `EnvelopeAutoSchema` finds the request/query serializers in the view
method's own source (so the schema can never drift from the code) and wraps
every response in the envelope. Responses stay generic on purpose: `data` is a
free object.
"""

import functools
import inspect
import re
from typing import Any

from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, inline_serializer
from rest_framework import serializers
from rest_framework.serializers import Serializer

SAFE_METHODS = {"get", "head", "options"}
_BODY = re.compile(r"(\w+)\.parse\(\s*request\.data\s*\)")
_QUERY = re.compile(r"(\w+)\.parse\(\s*request\.query_params\.dict\(\)\s*\)")

# Segment after /projects/<id>/ -> tag; everything else uses its first segment.
PROJECT_TAGS = {
    "tasks": "tasks",
    "notes": "notes",
    "statuses": "statuses",
    "priorities": "priorities",
    "members": "members",
    "join-requests": "join requests",
    "join-code": "projects",
    "integrations": "integrations",
    "attachments": "attachments",
    "storage": "attachments",
    "activity": "activity",
    "kanban-preference": "tasks",
    "transfer": "ownership transfer",
    "leave": "members",
}

ERROR_STATUSES = {
    400: "Validation failed, or the request was malformed.",
    401: "Not signed in.",
    403: "Not allowed (permission, CSRF or confirmation failed).",
    404: "Not found, or not visible to you.",
    409: "Conflicts with the current state.",
    429: "Too many requests. See the Retry-After header.",
}


@functools.cache
def _error_serializer() -> type[Serializer]:
    return inline_serializer(
        "ErrorEnvelope",
        {
            "success": serializers.BooleanField(),
            "status_code": serializers.IntegerField(),
            "message": serializers.CharField(),
            "errors": serializers.ListField(child=serializers.DictField()),
            "code": serializers.CharField(
                help_text="Stable machine-readable error code."
            ),
        },
    )


@functools.cache
def _envelope() -> type[Serializer]:
    return inline_serializer(
        "Envelope",
        {
            "success": serializers.BooleanField(),
            "status_code": serializers.IntegerField(),
            "message": serializers.CharField(),
            "data": serializers.JSONField(
                allow_null=True, help_text="Payload; shape depends on the endpoint."
            ),
            "meta": serializers.DictField(
                help_text="Pagination (count, limit, offset, next, previous) and extras."
            ),
        },
    )


def declared_serializers(view: Any, method: str) -> tuple[type | None, type | None]:
    """(request body serializer, query serializer) for a view method: an
    explicit `request_serializers` / `query_serializers` dict on the view wins,
    otherwise they are read from the `X.parse(request.data)` calls in its code."""
    explicit_body = getattr(view, "request_serializers", {}).get(method)
    explicit_query = getattr(view, "query_serializers", {}).get(method)
    handler = getattr(view, method, None)
    if handler is None:
        return explicit_body, explicit_query
    try:
        source = inspect.getsource(handler)
    except OSError, TypeError:
        return explicit_body, explicit_query
    namespace = getattr(inspect.getmodule(handler), "__dict__", {})
    body = explicit_body or _lookup(_BODY, source, namespace)
    query = explicit_query or _lookup(_QUERY, source, namespace)
    return body, query


def _lookup(pattern: re.Pattern, source: str, namespace: dict) -> type | None:
    match = pattern.search(source)
    found = namespace.get(match.group(1)) if match else None
    return found if inspect.isclass(found) and issubclass(found, Serializer) else None


class EnvelopeAutoSchema(AutoSchema):
    def _method(self) -> str:
        return self.method.lower()

    def get_tags(self) -> list[str]:
        parts = [p for p in self.path.split("/") if p and not p.startswith("{")]
        parts = [p for p in parts if p != "api"]
        if parts[:1] == ["projects"]:
            rest = [p for p in self.path.split("/") if p][2:]
            segments = [p for p in rest if not p.startswith("{")]
            if len(segments) >= 2 or (segments and segments[0] != "projects"):
                for segment in segments:
                    if segment in PROJECT_TAGS:
                        return [PROJECT_TAGS[segment]]
            return ["projects"]
        if parts[:1] == ["integrations"]:
            return ["provider callbacks"]
        if parts[:2] == ["me", "integrations"]:
            return ["integrations"]
        return [parts[0]] if parts else ["api"]

    def get_request_serializer(self) -> Any:
        body, _ = declared_serializers(self.view, self._method())
        return body

    def get_response_serializers(self) -> Any:
        ok = _envelope()
        responses: dict[int, Any] = {200: ok}
        if self._method() == "post":
            responses[201] = ok
        err = _error_serializer()
        statuses = set(ERROR_STATUSES)
        if not self._requires_login():
            statuses.discard(401)
        for status in sorted(statuses):
            responses[status] = err
        return responses

    def get_override_parameters(self) -> list[OpenApiParameter]:
        params: list[OpenApiParameter] = []
        _, query = declared_serializers(self.view, self._method())
        if query is not None:
            params.extend(_query_parameters(query))
        if self._is_paginated() and not {"limit", "offset"} & {p.name for p in params}:
            params.extend(_pagination_parameters())
        if self._method() not in SAFE_METHODS and self._uses_session():
            params.append(
                OpenApiParameter(
                    "X-CSRFToken",
                    OpenApiTypes.STR,
                    OpenApiParameter.HEADER,
                    required=True,
                    description="Value of the csrftoken cookie (GET /api/csrf/ sets it).",
                )
            )
        return params

    def _is_paginated(self) -> bool:
        handler = getattr(self.view, self._method(), None)
        try:
            source = inspect.getsource(handler)
        except OSError, TypeError:
            return False
        return any(
            marker in source for marker in ("paginated(", "paginate_queryset", "_list(")
        )

    def get_auth(self) -> list[dict[str, list]]:
        return [{"sessionAuth": []}] if self._requires_login() else []

    def _uses_session(self) -> bool:
        return bool(getattr(self.view, "authentication_classes", ()))

    def _requires_login(self) -> bool:
        from rest_framework.permissions import AllowAny

        classes = getattr(self.view, "permission_classes", ())
        return self._uses_session() and not any(c is AllowAny for c in classes)

    def get_operation_id(self) -> str:
        """`task_list_get`: the view's name plus the method, unique per route."""
        name = type(self.view).__name__.removesuffix("View")
        snake = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
        return f"{snake}_{self._method()}"

    def get_description(self) -> str:
        return inspect.getdoc(getattr(self.view, self._method(), None)) or (
            inspect.getdoc(self.view.__class__) or ""
        )

    def get_summary(self) -> str | None:
        return None


def _pagination_parameters() -> list[OpenApiParameter]:
    return [
        OpenApiParameter(
            "limit",
            OpenApiTypes.INT,
            OpenApiParameter.QUERY,
            description="Page size (default 25, at most 100).",
        ),
        OpenApiParameter(
            "offset",
            OpenApiTypes.INT,
            OpenApiParameter.QUERY,
            description="How many items to skip.",
        ),
    ]


def _query_parameters(serializer_class: type[Serializer]) -> list[OpenApiParameter]:
    params = []
    for name, field in serializer_class().fields.items():
        params.append(
            OpenApiParameter(
                name,
                _openapi_type(field),
                OpenApiParameter.QUERY,
                required=field.required,
                description=str(field.help_text or ""),
                enum=list(getattr(field, "choices", {}) or []) or None,
            )
        )
    return params


def _openapi_type(field: serializers.Field) -> Any:
    mapping = {
        serializers.IntegerField: OpenApiTypes.INT,
        serializers.BooleanField: OpenApiTypes.BOOL,
        serializers.UUIDField: OpenApiTypes.UUID,
        serializers.DateField: OpenApiTypes.DATE,
        serializers.DateTimeField: OpenApiTypes.DATETIME,
    }
    # DateTimeField is a subclass of nothing in DateField, but order matters for
    # the generic fallback below.
    for field_class, kind in mapping.items():
        if type(field) is field_class:
            return kind
    return OpenApiTypes.STR


def filter_api_paths(endpoints: list[tuple]) -> list[tuple]:
    """Only the public API: no admin, no schema/doc routes themselves."""
    return [
        endpoint
        for endpoint in endpoints
        if endpoint[0].startswith("/api/")
        and not endpoint[0].startswith(("/api/schema", "/api/docs"))
    ]
