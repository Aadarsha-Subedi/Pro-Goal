from rest_framework import serializers

from common.serializers.base import StrictSerializer
from security.constants.events import EventType


class EventQuerySerializer(StrictSerializer):
    event_type = serializers.ChoiceField(choices=EventType.choices, required=False)
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)
