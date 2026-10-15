from rest_framework import serializers

from common.serializers.base import StrictSerializer
from projects.constants import fields
from projects.constants.statuses import JoinRequestStatus


class JoinSerializer(StrictSerializer):
    code = serializers.CharField(max_length=fields.JOIN_CODE_INPUT_MAX_LENGTH)


class JoinRequestQuerySerializer(StrictSerializer):
    status = serializers.ChoiceField(
        choices=JoinRequestStatus.choices,
        required=False,
        default=JoinRequestStatus.PENDING,
    )
    limit = serializers.IntegerField(required=False)
    offset = serializers.IntegerField(required=False)


class RemoveMemberSerializer(StrictSerializer):
    """`reassign` maps an owned-item type to the member who inherits it,
    e.g. {"tasks": "<user id>"}. Types left out become unassigned."""

    reassign = serializers.DictField(
        child=serializers.UUIDField(),
        required=False,
        default=dict,
    )
