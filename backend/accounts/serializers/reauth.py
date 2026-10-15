from rest_framework import serializers

from common.serializers.base import StrictSerializer


class ReauthSerializer(StrictSerializer):
    """Proof of identity for sensitive actions: password, or a fresh Google token."""

    password = serializers.CharField(
        required=False, allow_null=True, max_length=128, trim_whitespace=False
    )
    id_token = serializers.CharField(required=False, allow_null=True, max_length=4096)
