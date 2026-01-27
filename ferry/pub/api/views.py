from typing import Any

from django.db import models, transaction
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from ferry.accounts.models import Person
from ferry.pub.api.serializers import (
    PubEventAddRemoveAttendeeSerializer,
    PubEventAttendanceTombstoneCreateSerializer,
    PubEventAttendanceTombstoneSerializer,
    PubEventBookingCreateSerializer,
    PubEventSerializer,
    PubEventTableSerializer,
    PublicPubEventSerializer,
    PubSerializer,
)
from ferry.pub.models import (
    Pub,
    PubEvent,
    PubEventAttendanceTombstone,
    PubEventBooking,
    PubEventQuerySet,
    PubEventRSVP,
    PubEventRSVPMethod,
    PubQuerySet,
    PubTable,
)


@extend_schema_view(
    list=extend_schema(tags=["Pub - Pubs"]),
    retrieve=extend_schema(tags=["Pub - Pubs"]),
)
class PubViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = PubSerializer

    def get_queryset(self) -> PubQuerySet:
        assert self.request.user.is_authenticated
        return Pub.objects.for_user(self.request.user)


class PubEventObjectPermission(permissions.BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method in ["PUT", "PATCH", "DELETE"]:
            return True

        if request.method == "POST":
            return request.user.has_perm("pub.create_event")

        return False

    def has_object_permission(self, request: Request, view: Any, pub_event: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == "POST":
            # For custom POST actions, check edit permission
            # This covers actions like booking, table, etc.
            return request.user.has_perm("pub.edit_event", pub_event)

        if request.method in ["PUT", "PATCH"]:
            return request.user.has_perm("pub.edit_event", pub_event)

        if request.method == "DELETE":
            return request.user.has_perm("pub.delete_event", pub_event)

        return False


@extend_schema_view(
    list=extend_schema(tags=["Pub - Events"]),
    retrieve=extend_schema(tags=["Pub - Events"]),
    update=extend_schema(tags=["Pub - Events"]),
    partial_update=extend_schema(tags=["Pub - Events"]),
    create=extend_schema(tags=["Pub - Events"]),
)
class PubEventViewset(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = PubEventSerializer
    permission_classes = [permissions.IsAuthenticated, PubEventObjectPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("discord_id",)

    def get_queryset(self) -> PubEventQuerySet:
        assert self.request.user.is_authenticated
        return PubEvent.objects.for_user(self.request.user)

    def perform_create(self, serializer: PubEventSerializer) -> None:  # type: ignore[override]
        with transaction.atomic():
            pub_event = serializer.save()
            # Get all unused tombstones for the next pub
            unused_tombstones = PubEventAttendanceTombstone.objects.filter(pub_event__isnull=True)

            rsvps = [
                PubEventRSVP(person=person, pub_event=pub_event, is_attending=True, method=PubEventRSVPMethod.AUTO)
                for person in Person.objects.filter(autopub=True).exclude(
                    id__in=unused_tombstones.values_list("person", flat=True)
                )
            ]
            if unused_tombstones.exists():
                rsvps.extend(
                    [
                        PubEventRSVP(
                            person=person, pub_event=pub_event, is_attending=False, method=PubEventRSVPMethod.TOMBSTONE
                        )
                        for person in Person.objects.filter(
                            autopub=True, id__in=unused_tombstones.values_list("person", flat=True)
                        )
                    ]
                )

            # Create the RSVPs for the new event
            PubEventRSVP.objects.bulk_create(rsvps)
            # Link the tombstones to the new event
            unused_tombstones.update(pub_event=pub_event)

    @extend_schema(
        tags=["Pub - Event Attendance"],
        request=PubEventAddRemoveAttendeeSerializer,
        responses={200: PubEventSerializer},
        description="Add a person to a pub event.",
    )
    @action(url_path="attendees/add", detail=True, methods=["POST"])
    def attendee_add(self, request: Request, pk: None = None) -> Response:
        pub_event: PubEvent = self.get_object()

        attendee_info = PubEventAddRemoveAttendeeSerializer(data=request.data)
        attendee_info.is_valid(raise_exception=True)

        person = attendee_info.validated_data["person"]

        # Update or create RSVP, ensuring it's marked as attending via DISCORD
        # This handles TOMBSTONE RSVPs by updating them to DISCORD
        PubEventRSVP.objects.update_or_create(
            pub_event=pub_event,
            person=person,
            defaults={"is_attending": True, "method": PubEventRSVPMethod.DISCORD},
        )

        # Note that we do not remove a tombstone here intentionally.

        serializer = PubEventSerializer(instance=pub_event)
        return Response(serializer.data)

    @extend_schema(
        tags=["Pub - Event Attendance"],
        request=PubEventAddRemoveAttendeeSerializer,
        responses={200: PubEventSerializer},
        description="Remove a person from a pub event.",
    )
    @action(url_path="attendees/remove", detail=True, methods=["POST"])
    def attendee_remove(self, request: Request, pk: None = None) -> Response:
        pub_event: PubEvent = self.get_object()

        attendee_info = PubEventAddRemoveAttendeeSerializer(data=request.data)
        attendee_info.is_valid(raise_exception=True)

        # Delete any RSVPs using Discord for that event
        rsvp_qs = PubEventRSVP.objects.filter(
            pub_event=pub_event, person=attendee_info.validated_data["person"], method=PubEventRSVPMethod.DISCORD
        )
        rsvp_qs.delete()

        # Note: the bot checks if the user is still present, i.e if they have opted in via
        # another method
        serializer = PubEventSerializer(instance=pub_event)
        return Response(serializer.data)

    @extend_schema(
        tags=["Pub - Event Attendance"],
        request=PubEventTableSerializer,
        responses={200: PubEventSerializer},
        description="Update the table number for a pub event.",
    )
    @action(detail=True, methods=["POST"])
    def table(self, request: Request, pk: None = None) -> Response:
        pub_event: PubEvent = self.get_object()

        table_info = PubEventTableSerializer(data=request.data)
        table_info.is_valid(raise_exception=True)

        table, _ = PubTable.objects.get_or_create(
            pub=pub_event.pub,
            number=table_info.validated_data["table_number"],
        )

        pub_event.table = table
        pub_event.save()

        serializer = PubEventSerializer(instance=pub_event)
        return Response(serializer.data)

    @extend_schema(
        tags=["Pub - Event Booking"],
        request=PubEventBookingCreateSerializer,
        responses={200: PubEventSerializer, 400: None},
        description="Create a booking for a pub event.",
    )
    @action(detail=True, methods=["POST"])
    def booking(self, request: Request, pk: None = None) -> Response:
        pub_event: PubEvent = self.get_object()

        try:
            _ = pub_event.booking
            return Response({"error": "A booking already exists for this event."}, status=409)
        except PubEventBooking.DoesNotExist:
            pass

        booking_info = PubEventBookingCreateSerializer(data=request.data)
        booking_info.is_valid(raise_exception=True)

        PubEventBooking.objects.create(
            pub_event=pub_event,
            created_by=booking_info.validated_data["created_by"],
            table_size=booking_info.validated_data["table_size"],
        )

        # Refresh the object to load the booking relationship
        pub_event.refresh_from_db()

        serializer = PubEventSerializer(instance=pub_event)
        return Response(serializer.data)

    @extend_schema(
        tags=["Pub - Next Pub"],
        responses={200: PublicPubEventSerializer, 204: None},
        description="Get the next pub event. This endpoint does not require authentication.",
    )
    @action(detail=False, methods=["GET"], permission_classes=[permissions.AllowAny])
    def next(self, request: Request) -> Response:
        if next_pub := PubEvent.objects.get_next():
            serializer = PublicPubEventSerializer(instance=next_pub)
            return Response(serializer.data)
        else:
            return Response(status=204)

    @extend_schema(
        tags=["Pub - Event Attendance"],
        request=PubEventAttendanceTombstoneCreateSerializer,
        responses={200: PubEventAttendanceTombstoneSerializer, 409: None},
        description="Create a tombstone for a person to skip the next pub.",
    )
    @action(url_path="tombstones", detail=False, methods=["POST"])
    def create_tombstone(self, request: Request, pk: None = None) -> Response:
        tombstone_info = PubEventAttendanceTombstoneCreateSerializer(data=request.data)
        tombstone_info.is_valid(raise_exception=True)

        with transaction.atomic():
            # Get the next pub event, if there is one.
            # If there is one, we will automatically link the tombstone to the event.
            pub_event = PubEvent.objects.get_next()

            # Check if the person already has a tombstone
            if (
                PubEventAttendanceTombstone.objects.filter(person=tombstone_info.validated_data["person"])
                .filter(models.Q(pub_event=pub_event) if pub_event else models.Q(pub_event__isnull=True))
                .exists()
            ):
                return Response(
                    {"error": "This person already has a tombstone for this event or the next pub."}, status=409
                )

            tombstone = PubEventAttendanceTombstone.objects.create(
                pub_event=pub_event,
                person=tombstone_info.validated_data["person"],
            )

            # Update any RSVPs using AutoPub for the event, if it exists.
            if pub_event:
                rsvps = PubEventRSVP.objects.filter(
                    pub_event=pub_event,
                    person=tombstone_info.validated_data["person"],
                    method=PubEventRSVPMethod.AUTO,
                )
                rsvps.update(method=PubEventRSVPMethod.TOMBSTONE, is_attending=False)

        serializer = PubEventAttendanceTombstoneSerializer(instance=tombstone)
        return Response(serializer.data)
