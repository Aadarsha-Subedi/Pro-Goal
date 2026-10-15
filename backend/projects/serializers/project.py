from rest_framework import serializers

from accounts.serializers.reauth import ReauthSerializer
from common.serializers.base import StrictSerializer
from projects.constants import fields


class ProjectCreateSerializer(StrictSerializer):
    name = serializers.CharField(max_length=fields.PROJECT_NAME_MAX_LENGTH)
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=fields.PROJECT_DESCRIPTION_MAX_LENGTH,
    )
    task_key = serializers.RegexField(fields.TASK_KEY_PATTERN)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=fields.TAG_MAX_LENGTH),
        required=False,
        max_length=fields.MAX_TAGS_PER_PROJECT * 3,
    )


class ProjectUpdateSerializer(StrictSerializer):
    name = serializers.CharField(
        required=False, max_length=fields.PROJECT_NAME_MAX_LENGTH
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=fields.PROJECT_DESCRIPTION_MAX_LENGTH,
    )
    task_key = serializers.RegexField(fields.TASK_KEY_PATTERN, required=False)
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=fields.TAG_MAX_LENGTH),
        required=False,
        max_length=fields.MAX_TAGS_PER_PROJECT * 3,
    )
    is_listed = serializers.BooleanField(required=False)


class ProjectCopySerializer(StrictSerializer):
    name = serializers.CharField(
        required=False, max_length=fields.PROJECT_NAME_MAX_LENGTH
    )


__all__ = [
    "ProjectCopySerializer",
    "ProjectCreateSerializer",
    "ProjectUpdateSerializer",
    "ReauthSerializer",
]
