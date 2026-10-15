from rest_framework import serializers

from common.serializers.base import StrictSerializer
from integrations.constants.statuses import DeliveryStatus


class DeliveryQuerySerializer(StrictSerializer):
    status = serializers.ChoiceField(choices=DeliveryStatus.choices, required=False)
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)
