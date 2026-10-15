from rest_framework import serializers

from common.serializers.base import StrictSerializer
from tracker.constants import fields


class CommentSerializer(StrictSerializer):
    body = serializers.CharField(max_length=fields.COMMENT_BODY_MAX_LENGTH)
