from rest_framework import serializers

from common.serializers.base import StrictSerializer
from tracker.constants.categories import GroupBy, SortBy


class PreferenceSerializer(StrictSerializer):
    group_by = serializers.ChoiceField(choices=GroupBy.choices)
    sort_by = serializers.ChoiceField(choices=SortBy.choices)
