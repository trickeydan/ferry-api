from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from ferry.pub.api.serializers import (
    PubEventAddRemoveAttendeeSerializer,
    PubEventSerializer,
    PubEventTableSerializer,
    PubSerializer,
)
from ferry.pub.models import Pub, PubEvent, PubEventQuerySet, PubEventRSVP, PubQuerySet, PubTable


@extend_schema_view(
    list=extend_schema(tags=["Pub - Pubs"]),
    retrieve=extend_schema(tags=["Pub - Pubs"]),
)
class PubViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = PubSerializer

    def get_queryset(self) -> PubQuerySet:
        assert self.request.user.is_authenticated
        return Pub.objects.for_user(self.request.user)


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
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("discord_id",)

    def get_queryset(self) -> PubEventQuerySet:
        assert self.request.user.is_authenticated
        return PubEvent.objects.for_user(self.request.user)

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

        rsvp, created = PubEventRSVP.objects.get_or_create(
            pub_event=pub_event, person=attendee_info.validated_data["person"], defaults={"is_attending": True}
        )
        if not created:
            rsvp.is_attending = True
            rsvp.save()

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

        rsvp, created = PubEventRSVP.objects.get_or_create(
            pub_event=pub_event, person=attendee_info.validated_data["person"], defaults={"is_attending": False}
        )
        if not created:
            rsvp.is_attending = False
            rsvp.save()

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
