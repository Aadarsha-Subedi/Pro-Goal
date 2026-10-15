from rest_framework import serializers

from common.serializers.base import StrictSerializer
from tracker.constants import fields

_tags = serializers.ListField(
    child=serializers.CharField(max_length=30),
    required=False,
    max_length=fields.MAX_TAGS_PER_ITEM * 3,
)


class NoteCreateSerializer(StrictSerializer):
    title = serializers.CharField(max_length=fields.NOTE_TITLE_MAX_LENGTH)
    # Size is checked in bytes by the service (100 KB).
    body = serializers.CharField(required=False, allow_blank=True)
    tags = _tags


class NoteUpdateSerializer(StrictSerializer):
    version = serializers.IntegerField(min_value=1)
    title = serializers.CharField(
        max_length=fields.NOTE_TITLE_MAX_LENGTH, required=False
    )
    body = serializers.CharField(required=False, allow_blank=True)
    tags = _tags


class NoteQuerySerializer(StrictSerializer):
    q = serializers.CharField(required=False, max_length=fields.SEARCH_MAX_LENGTH)
    tag = serializers.CharField(required=False, max_length=30)
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)
