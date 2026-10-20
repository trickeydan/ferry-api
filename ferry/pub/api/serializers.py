from typing import Any, Never

from rest_framework import serializers
from rest_framework.utils.serializer_helpers import ReturnDict

from ferry.accounts.api.serializers import PersonLinkForPubEventSerializer
from ferry.accounts.models import Person
from ferry.pub.models import Pub, PubEvent, PubEventAttendanceTombstone, PubEventBooking, PubTable
from ferry.pub.repository import get_attendance_tombstones_for_pub_event, get_attendees_for_pub_event


class PubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pub
        fields = ("id", "name", "emoji", "map_url", "menu_url", "booking_url")


class PubEventPubField(serializers.PrimaryKeyRelatedField):
    def use_pk_only_optimization(self) -> bool:
        return False

    def to_representation(self, value: Any) -> ReturnDict:
        return PubSerializer(instance=value).data


class PubLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pub
        fields = ("id", "name")


class PubTableSerializer(serializers.ModelSerializer):
    pub = PubLinkSerializer()

    class Meta:
        model = PubTable
        fields = ("id", "pub", "number")


class PubEventBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PubEventBooking
        fields = ("id", "table_size", "created_by")


class PubEventBookingCreateSerializer(serializers.Serializer):
    created_by = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all())
    table_size = serializers.IntegerField(max_value=1000, min_value=1, required=True)


class PubEventSerializer(serializers.ModelSerializer):
    pub = PubEventPubField(queryset=Pub.objects.all())
    attendees = serializers.SerializerMethodField("get_attendees")
    tombstoned_attendees = serializers.SerializerMethodField("get_tombstoned_attendees")
    announcements = serializers.SerializerMethodField("get_announcements")
    table = PubTableSerializer(read_only=True)
    booking = PubEventBookingSerializer(read_only=True)
    expected_booker = serializers.SerializerMethodField("get_expected_booker")

    class Meta:
        model = PubEvent
        fields = (
            "id",
            "timestamp",
            "pub",
            "discord_id",
            "table",
            "attendees",
            "tombstoned_attendees",
            "announcements",
            "booking",
            "expected_booker",
            "created_by",
            "created_at",
            "updated_at",
        )

    def get_attendees(self, pub_event: PubEvent) -> ReturnDict:
        attendees = get_attendees_for_pub_event(pub_event)
        serializer = PersonLinkForPubEventSerializer(read_only=True, many=True, instance=attendees)
        return serializer.data

    def get_tombstoned_attendees(self, pub_event: PubEvent) -> ReturnDict | list[Never]:
        attendance_tombstones = get_attendance_tombstones_for_pub_event(pub_event)
        if not attendance_tombstones.exists():
            return []
        serializer = PersonLinkForPubEventSerializer(read_only=True, many=True, instance=attendance_tombstones)
        return serializer.data

    def get_announcements(self, pub_event: PubEvent) -> list[str]:
        extra_infos = pub_event.extra_info.order_by("created_at").all()
        return [ei.formatted_info for ei in extra_infos]

    def get_expected_booker(self, pub_event: PubEvent) -> ReturnDict | None:
        if PubEventBooking.objects.filter(pub_event=pub_event).exists():
            return None

        attendees = get_attendees_for_pub_event(pub_event)
        attendees_with_discord = {attendee for attendee in attendees if attendee.discord_id is not None}

        # Sort in Python to avoid additional query
        sorted_attendees = sorted(attendees_with_discord, key=lambda p: p.pub_booking_priority, reverse=True)
        if not sorted_attendees:
            return None

        expected_booker = sorted_attendees[0]

        serializer = PersonLinkForPubEventSerializer(read_only=True, instance=expected_booker)
        return serializer.data


class PublicPubEventSerializer(serializers.ModelSerializer):
    pub = PubSerializer()
    attendee_count = serializers.SerializerMethodField("get_attendee_count")

    class Meta:
        model = PubEvent
        fields = (
            "id",
            "timestamp",
            "pub",
            "attendee_count",
        )

    def get_attendee_count(self, event: PubEvent) -> int:
        return get_attendees_for_pub_event(event).count()


class PubEventAddRemoveAttendeeSerializer(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all())


class PubEventTableSerializer(serializers.Serializer):
    table_number = serializers.IntegerField(max_value=1000, min_value=1, required=True)


class PubEventAttendanceTombstoneCreateSerializer(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all())

    def validate_person(self, value: Person) -> Person:
        if not value.autopub:
            raise serializers.ValidationError("This person is not signed up for autopub.")
        return value


class PubEventAttendanceTombstoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = PubEventAttendanceTombstone
        fields = ("id", "person", "pub_event")  # Only IDs
