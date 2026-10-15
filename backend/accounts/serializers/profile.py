from rest_framework import serializers

from accounts.constants.fields import NAME_MAX_LENGTH
from common.serializers.base import StrictSerializer


class ProfileUpdateSerializer(StrictSerializer):
    first_name = serializers.CharField(max_length=NAME_MAX_LENGTH, required=False)
    last_name = serializers.CharField(max_length=NAME_MAX_LENGTH, required=False)
    display_name = serializers.CharField(max_length=NAME_MAX_LENGTH, required=False)


class AvatarUploadSerializer(StrictSerializer):
    file = serializers.FileField()
