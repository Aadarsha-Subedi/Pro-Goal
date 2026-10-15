from rest_framework import serializers

from projects.serializers.project import ReauthSerializer


class TransferStartSerializer(ReauthSerializer):
    to_user = serializers.UUIDField()
