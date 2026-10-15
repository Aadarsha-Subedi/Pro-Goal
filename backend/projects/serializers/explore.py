from rest_framework import serializers

from common.serializers.base import StrictSerializer


class ExploreQuerySerializer(StrictSerializer):
    q = serializers.CharField(required=False, max_length=100)
    tag = serializers.CharField(required=False, max_length=30)
    starts_after = serializers.DateField(required=False)
    ends_before = serializers.DateField(required=False)
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)


class TagSuggestionQuerySerializer(StrictSerializer):
    q = serializers.CharField(required=False, max_length=30)
