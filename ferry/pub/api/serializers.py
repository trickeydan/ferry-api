from rest_framework import serializers
from rest_framework.utils.serializer_helpers import ReturnDict

from ferry.accounts.models import Person
from ferry.court.api.serializers import PersonLinkWithDiscordIdSerializer
from ferry.pub.models import Pub, PubEvent, PubTable
from ferry.pub.repository import get_attendees_for_pub_event


class PubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pub
        fields = ("id", "name", "emoji", "map_url", "menu_url")


class PubLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pub
        fields = ("id", "name")


class PubTableSerializer(serializers.ModelSerializer):
    pub = PubLinkSerializer()

    class Meta:
        model = PubTable
        fields = ("id", "pub", "number")


class PubEventSerializer(serializers.ModelSerializer):
    attendees = serializers.SerializerMethodField("get_attendees")
    table = PubTableSerializer(read_only=True)

    class Meta:
        model = PubEvent
        fields = (
            "id",
            "timestamp",
            "pub",
            "discord_id",
            "table",
            "attendees",
            "created_by",
            "created_at",
            "updated_at",
        )

    def get_attendees(self, pub_event: PubEvent) -> ReturnDict:
        attendees = get_attendees_for_pub_event(pub_event)
        serializer = PersonLinkWithDiscordIdSerializer(read_only=True, many=True, instance=attendees)
        return serializer.data


class PublicPubEventSerializer(serializers.ModelSerializer):
    pub = PubSerializer()

    class Meta:
        model = PubEvent
        fields = (
            "id",
            "timestamp",
            "pub",
        )


class PubEventAddRemoveAttendeeSerializer(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all())


class PubEventTableSerializer(serializers.Serializer):
    table_number = serializers.IntegerField(max_value=1000, min_value=1, required=True)
