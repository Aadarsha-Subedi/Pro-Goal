from datetime import date

from django.db.models import F, Prefetch, Q, QuerySet
from django.utils import timezone
from django_filters import rest_framework as filters

from accounts.models import User
from common.exception.domain import ValidationException
from projects.models import Membership
from tracker.constants import error_codes, fields, messages
from tracker.constants.categories import StatusCategory
from tracker.models import Task

# Public sort name -> ORM field. A leading "-" on the request reverses it.
SORT_FIELDS = {
    "number": "number",
    "title": "title",
    "due_date": "due_date",
    "priority": "priority__rank",
    "created_at": "created_at",
    "updated_at": "updated_at",
}
DEFAULT_SORT = "-number"


def today() -> date:
    """The server's UTC date: the only clock that decides what is overdue."""
    return timezone.now().date()


def base_queryset(**filters_: object) -> QuerySet[Task]:
    return (
        Task.objects.filter(**filters_)
        .select_related("project", "status", "priority", "created_by", "parent")
        .prefetch_related(
            "task_assignees__user",
            "task_tags__tag",
            Prefetch(
                "subtasks",
                queryset=Task.objects.select_related("status"),
                to_attr="live_subtasks",
            ),
        )
    )


class TaskFilter(filters.FilterSet):
    status = filters.UUIDFilter(field_name="status_id")
    priority = filters.UUIDFilter(field_name="priority_id")
    assignee = filters.UUIDFilter(field_name="task_assignees__user_id")
    tag = filters.CharFilter(method="filter_tag")
    due_date = filters.DateFromToRangeFilter()
    q = filters.CharFilter(method="filter_search", max_length=fields.SEARCH_MAX_LENGTH)
    overdue = filters.BooleanFilter(method="filter_overdue")
    top_level = filters.BooleanFilter(method="filter_top_level")

    class Meta:
        model = Task
        fields: list[str] = []

    def filter_tag(self, queryset, name, value):
        return queryset.filter(task_tags__tag__name=value.strip().lower())

    def filter_search(self, queryset, name, value):
        return queryset.filter(title__icontains=value.strip())

    def filter_overdue(self, queryset, name, value):
        overdue = Q(due_date__lt=today()) & ~Q(status__category=StatusCategory.DONE)
        return queryset.filter(overdue) if value else queryset.exclude(overdue)

    def filter_top_level(self, queryset, name, value):
        return queryset.filter(parent__isnull=value)


def apply_filters(queryset: QuerySet[Task], params) -> QuerySet[Task]:
    task_filter = TaskFilter(params, queryset=queryset)
    if not task_filter.is_valid():
        raise ValidationException(
            errors=[
                {"field": name, "message": " ".join(errors)}
                for name, errors in task_filter.errors.items()
            ]
        )
    return task_filter.qs.distinct()


def apply_ordering(queryset: QuerySet[Task], value: str | None) -> QuerySet[Task]:
    value = value or DEFAULT_SORT
    descending = value.startswith("-")
    name = value.lstrip("-")
    field = SORT_FIELDS.get(name)
    if field is None:
        raise ValidationException(
            errors=[{"field": "ordering", "message": messages.INVALID_SORT}],
            error_code=error_codes.INVALID_SORT,
        )
    expression = F(field)
    expression = (
        expression.desc(nulls_last=True)
        if descending
        else expression.asc(nulls_last=True)
    )
    return queryset.order_by(expression, "-number")


def project_tasks(membership: Membership, params) -> QuerySet[Task]:
    queryset = base_queryset(project=membership.project)
    return apply_ordering(apply_filters(queryset, params), params.get("ordering"))


def subtasks_of(parent: Task) -> QuerySet[Task]:
    return base_queryset(parent=parent).order_by("number")


def my_tasks(user: User, params) -> QuerySet[Task]:
    """Tasks assigned to `user` in projects they still belong to."""
    queryset = base_queryset(
        task_assignees__user=user,
        project__is_deleted=False,
        project__memberships__user=user,
    )
    return apply_ordering(apply_filters(queryset, params), params.get("ordering"))
