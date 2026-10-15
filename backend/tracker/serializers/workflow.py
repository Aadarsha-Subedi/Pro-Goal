from rest_framework import serializers

from common.serializers.base import StrictSerializer
from tracker.constants import fields
from tracker.constants.categories import StatusCategory


class StatusCreateSerializer(StrictSerializer):
    name = serializers.CharField(max_length=fields.STATUS_NAME_MAX_LENGTH)
    category = serializers.ChoiceField(choices=StatusCategory.choices)
    position = serializers.IntegerField(required=False, min_value=0)
    is_default = serializers.BooleanField(required=False, default=False)


class StatusUpdateSerializer(StrictSerializer):
    name = serializers.CharField(
        max_length=fields.STATUS_NAME_MAX_LENGTH, required=False
    )
    category = serializers.ChoiceField(choices=StatusCategory.choices, required=False)
    position = serializers.IntegerField(required=False, min_value=0)
    is_default = serializers.BooleanField(required=False)


class PriorityCreateSerializer(StrictSerializer):
    name = serializers.CharField(max_length=fields.PRIORITY_NAME_MAX_LENGTH)
    position = serializers.IntegerField(required=False, min_value=0)
    is_default = serializers.BooleanField(required=False, default=False)


class PriorityUpdateSerializer(StrictSerializer):
    name = serializers.CharField(
        max_length=fields.PRIORITY_NAME_MAX_LENGTH, required=False
    )
    position = serializers.IntegerField(required=False, min_value=0)
    is_default = serializers.BooleanField(required=False)


class MoveToSerializer(StrictSerializer):
    """Body of a delete: where to move tasks that still use the item."""

    move_to = serializers.UUIDField(required=False, allow_null=True)
