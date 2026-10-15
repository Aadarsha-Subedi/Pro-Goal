"""The explore page: projects their owners chose to list. Visitors see enough
to decide to ask to join (name, description, tags, dates, owner first name,
member count) and nothing inside the project."""

from datetime import date, timedelta

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from accounts.models import User
from common.validators.tags import normalize_tags
from projects.constants import limits
from projects.constants.statuses import JoinRequestStatus
from projects.models import JoinRequest, Membership, Project, ProjectTag

MAX_SUGGESTED_TAGS = 20


def _visible() -> QuerySet[Project]:
    """Listed, not archived, not deleted (the default manager hides deleted)."""
    return Project.objects.filter(is_listed=True, archived_at__isnull=True)


def listed_projects(
    user: User,
    *,
    q: str | None = None,
    tags: list[str] | None = None,
    starts_after: date | None = None,
    ends_before: date | None = None,
) -> QuerySet[Project]:
    queryset = (
        _visible()
        .exclude(pk__in=Membership.objects.filter(user=user).values("project_id"))
        .select_related("owner")
        .prefetch_related("project_tags__tag")
        .annotate(member_count=Count("memberships"))
    )
    if q:
        text = q.strip()
        queryset = queryset.filter(
            Q(name__icontains=text) | Q(description__icontains=text)
        )
    wanted = normalize_tags(tags or [])
    if wanted:
        queryset = queryset.filter(
            pk__in=ProjectTag.objects.filter(tag__name__in=wanted).values("project_id")
        )
    if starts_after:
        queryset = queryset.filter(start_date__gte=starts_after)
    if ends_before:
        queryset = queryset.filter(end_date__lte=ends_before)
    return queryset.order_by("-listed_at", "-created_at")


def my_request_states(user: User) -> dict:
    """project id -> "pending" or the time a rejected user may ask again."""
    cooldown = timedelta(hours=limits.JOIN_REQUEST_RETRY_HOURS)
    now = timezone.now()
    states: dict = {}
    recent = JoinRequest.objects.filter(user=user).filter(
        Q(status=JoinRequestStatus.PENDING)
        | Q(status=JoinRequestStatus.REJECTED, decided_at__gt=now - cooldown)
    )
    for request in recent:
        if request.status == JoinRequestStatus.PENDING:
            states[request.project_id] = {"state": "pending", "cooldown_until": None}
        elif request.project_id not in states:
            states[request.project_id] = {
                "state": "cooldown",
                "cooldown_until": (request.decided_at + cooldown).isoformat(),
            }
    return states


def suggest_tags(q: str | None = None) -> list[dict]:
    """The tags most used by listed projects (name and how many)."""
    rows = ProjectTag.objects.filter(
        project__is_listed=True,
        project__archived_at__isnull=True,
        project__is_deleted=False,
    )
    if q:
        rows = rows.filter(tag__name__icontains=q.strip().lower())
    ranked = (
        rows.values("tag__name")
        .annotate(projects=Count("project", distinct=True))
        .order_by("-projects", "tag__name")[:MAX_SUGGESTED_TAGS]
    )
    return [{"name": row["tag__name"], "projects": row["projects"]} for row in ranked]
