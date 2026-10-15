from rest_framework import serializers

from common.serializers.base import StrictSerializer


class _GrantFields(StrictSerializer):
    """A set of permissions: either an explicit list of codes or a preset."""

    permissions = serializers.ListField(
        child=serializers.CharField(max_length=64), required=False, max_length=100
    )
    preset = serializers.CharField(required=False, max_length=32)

    def validate(self, attrs: dict) -> dict:
        if "permissions" in attrs and "preset" in attrs:
            raise serializers.ValidationError(
                "Send either permissions or preset, not both."
            )
        return attrs


class GrantReplaceSerializer(_GrantFields):
    """PUT: the new full set. One of the two fields is required."""

    def validate(self, attrs: dict) -> dict:
        attrs = super().validate(attrs)
        if not attrs:
            raise serializers.ValidationError("Send permissions or preset.")
        return attrs


class ApproveSerializer(_GrantFields):
    """Optional starting permissions when approving a join request."""
