from rest_framework import serializers

from attachments.constants.limits import FILENAME_MAX_LENGTH
from attachments.constants.types import TargetType
from common.serializers.base import StrictSerializer


class UploadRequestSerializer(StrictSerializer):
    """`target` is a task number, or a note or comment id (uuid)."""

    target_type = serializers.ChoiceField(choices=TargetType.choices)
    target = serializers.CharField(max_length=64)
    filename = serializers.CharField(max_length=FILENAME_MAX_LENGTH * 2)
    content_type = serializers.CharField(max_length=127)
    size = serializers.IntegerField(min_value=1)

    def validate(self, attrs: dict) -> dict:
        target, kind = attrs["target"], attrs["target_type"]
        if kind == TargetType.TASK:
            if not target.isdigit() or int(target) < 1:
                raise serializers.ValidationError({"target": "Enter a task number."})
            attrs["target"] = int(target)
        else:
            try:
                attrs["target"] = serializers.UUIDField().to_internal_value(target)
            except serializers.ValidationError:
                raise serializers.ValidationError({"target": "Enter an id."}) from None
        return attrs


class ListQuerySerializer(StrictSerializer):
    task = serializers.IntegerField(required=False, min_value=1)
    note = serializers.UUIDField(required=False)
    comment = serializers.UUIDField(required=False)
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)
