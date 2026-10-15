from rest_framework import serializers

from common.serializers.base import StrictSerializer
from tracker.constants import fields


class _TaskFields(StrictSerializer):
    status = serializers.UUIDField(required=False)
    priority = serializers.UUIDField(required=False)
    start_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    assignees = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        max_length=fields.MAX_ASSIGNEES,
    )
    tags = serializers.ListField(
        child=serializers.CharField(max_length=30),
        required=False,
        max_length=fields.MAX_TAGS_PER_ITEM * 3,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=fields.TASK_DESCRIPTION_MAX_LENGTH,
    )


class TaskCreateSerializer(_TaskFields):
    title = serializers.CharField(max_length=fields.TASK_TITLE_MAX_LENGTH)


class TaskUpdateSerializer(_TaskFields):
    title = serializers.CharField(
        max_length=fields.TASK_TITLE_MAX_LENGTH, required=False
    )
    parent = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class TaskListQuerySerializer(StrictSerializer):
    """Documents the filters of the task list (`tracker.services.query`)."""

    status = serializers.UUIDField(required=False, help_text="Status id.")
    priority = serializers.UUIDField(required=False, help_text="Priority id.")
    assignee = serializers.UUIDField(required=False, help_text="User id.")
    tag = serializers.CharField(required=False)
    q = serializers.CharField(required=False, help_text="Search in titles.")
    due_date_after = serializers.DateField(required=False)
    due_date_before = serializers.DateField(required=False)
    overdue = serializers.BooleanField(required=False)
    top_level = serializers.BooleanField(
        required=False, help_text="true hides subtasks."
    )
    ordering = serializers.CharField(
        required=False,
        help_text="number, title, due_date, priority, created_at or updated_at; prefix - to reverse.",
    )
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)
