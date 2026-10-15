from rest_framework import serializers

from common.serializers.base import StrictSerializer


class ActivityQuerySerializer(StrictSerializer):
    actor = serializers.UUIDField(required=False)
    action = serializers.CharField(required=False, max_length=64)
    entity_type = serializers.CharField(required=False, max_length=64)
    created_after = serializers.DateTimeField(required=False)
    created_before = serializers.DateTimeField(required=False)
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)
