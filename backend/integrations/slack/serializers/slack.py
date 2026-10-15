from rest_framework import serializers

from common.serializers.base import StrictSerializer


class MappingCreateSerializer(StrictSerializer):
    channel_id = serializers.CharField(max_length=32)
    enabled_events = serializers.ListField(
        child=serializers.CharField(max_length=32), max_length=20
    )


class MappingUpdateSerializer(StrictSerializer):
    enabled_events = serializers.ListField(
        child=serializers.CharField(max_length=32), max_length=20
    )


class PreferenceItemSerializer(StrictSerializer):
    slack_dm = serializers.BooleanField(required=False)
    email = serializers.BooleanField(required=False)


class PreferenceUpdateSerializer(StrictSerializer):
    preferences = serializers.DictField(
        child=PreferenceItemSerializer(), allow_empty=False
    )
