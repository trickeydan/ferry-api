import base64
from http import HTTPStatus
from typing import Any

from django.core.signing import TimestampSigner
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import exceptions, filters, permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from ferry.accounts.models import Person, PersonQuerySet, User
from ferry.court.models import (
    Accusation,
    AccusationQuerySet,
    Consequence,
    ConsequenceQuerySet,
    Ratification,
)

from .serializers import (
    AccusationCreateSerializer,
    AccusationSerializer,
    ConsequenceReadSerializer,
    ConsequenceSerializer,
    DiscordLinkTokenSerializer,
    PersonSerializer,
    RatificationCreateSerializer,
    RatificationSerializer,
)


class PeopleObjectPermission(permissions.BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method in ["PUT", "PATCH", "DELETE"]:
            return True

        if request.method == "POST":
            return request.user.has_perm("court.create_person")

        return False

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method in ["PUT", "PATCH"]:
            return request.user.has_perm("court.edit_person", obj)

        if request.method == "DELETE":
            return request.user.has_perm("court.delete_person", obj)

        return False


@extend_schema_view(
    list=extend_schema(tags=["People"]),
    retrieve=extend_schema(tags=["People"]),
    update=extend_schema(tags=["People"]),
    partial_update=extend_schema(tags=["People"]),
    create=extend_schema(tags=["People"]),
    destroy=extend_schema(tags=["People"]),
)
class PersonViewset(viewsets.ModelViewSet):
    serializer_class = PersonSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    permission_classes = [permissions.IsAuthenticated, PeopleObjectPermission]
    ordering_fields = ("display_name", "current_score", "created_at", "updated_at")
    filterset_fields = ("discord_id",)

    def get_queryset(self) -> PersonQuerySet:
        assert self.request.user.is_authenticated
        return Person.objects.for_user(self.request.user).with_current_score()

    def perform_update(self, serializer: serializers.BaseSerializer) -> None:
        assert serializer.instance
        if all(
            [
                serializer.instance.discord_id != serializer.validated_data.get("discord_id"),
                not serializer.context["request"].user.has_perm("court.assign_discord_id_to_person"),
            ]
        ):
            raise exceptions.PermissionDenied("You don't have permission to update a Discord ID directly.")
        return super().perform_update(serializer)

    @extend_schema(
        tags=["People"],
        responses={200: DiscordLinkTokenSerializer},
        description="This is used by the Discord bot only.",
    )
    @action(detail=True, methods=["GET"], permission_classes=[permissions.IsAuthenticated])
    def fact(self, request: Request, pk: None = None) -> Response:
        person = self.get_object()
        if not request.user.has_perm("court.act_for_person", person):
            raise exceptions.PermissionDenied("You don't have permission to get a FACT for that person.")

        try:
            _ = person.user
            link_token = None
        except User.DoesNotExist:
            signer = TimestampSigner()
            link_token = base64.b64encode(signer.sign(str(person.id)).encode()).decode()

        serializer = DiscordLinkTokenSerializer({"link_token": link_token, "fact": "bees"})
        return Response(serializer.data)


class ConsequenceObjectPermission(permissions.BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method in ["PUT", "PATCH", "DELETE"]:
            return True

        if request.method == "POST":
            return request.user.has_perm("court.create_consequence")

        return False

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method in ["PUT", "PATCH"]:
            return request.user.has_perm("court.edit_consequence", obj)

        if request.method == "DELETE":
            return request.user.has_perm("court.delete_consequence", obj)

        return False


@extend_schema_view(
    list=extend_schema(tags=["Ferry - Consequences"]),
    retrieve=extend_schema(tags=["Ferry - Consequences"]),
    update=extend_schema(tags=["Ferry - Consequences"]),
    partial_update=extend_schema(tags=["Ferry - Consequences"]),
    create=extend_schema(tags=["Ferry - Consequences"]),
    destroy=extend_schema(tags=["Ferry - Consequences"]),
)
class ConsequenceViewset(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    permission_classes = [permissions.IsAuthenticated, ConsequenceObjectPermission]
    ordering_fields = ("created_at", "updated_at")
    filterset_fields = ("is_enabled", "created_by")

    def get_serializer_class(self) -> type[ConsequenceSerializer] | type[ConsequenceReadSerializer]:
        if self.action == "create":
            return ConsequenceSerializer
        return ConsequenceReadSerializer

    def get_queryset(self) -> ConsequenceQuerySet:
        assert self.request.user.is_authenticated
        return Consequence.objects.for_user(self.request.user)


class AccusationObjectPermission(permissions.BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method in ["PUT", "PATCH", "DELETE"]:
            return True

        if request.method == "POST":
            return request.user.has_perm("court.create_accusation")

        return False

    def has_object_permission(self, request: Request, view: Any, obj: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method in ["PUT", "PATCH"]:
            return request.user.has_perm("court.edit_accusation", obj)

        if request.method == "DELETE":
            return request.user.has_perm("court.delete_accusation", obj)

        return False


class RatificationObjectPermission(permissions.BasePermission):
    def has_permission(self, request: Request, view: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method in ["PUT", "PATCH", "DELETE"]:
            return True

        if request.method == "POST":
            return request.user.has_perm("court.create_ratification")

        return False

    def has_object_permission(self, request: Request, view: Any, accusation: Any) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        if request.method == "POST":
            return True

        if request.method in ["PUT", "PATCH"]:
            return request.user.has_perm("court.edit_ratification", accusation.ratification)

        if request.method == "DELETE":
            return request.user.has_perm("court.delete_ratification", accusation.ratification)

        return False


@extend_schema_view(
    list=extend_schema(tags=["Ferry - Accusations"]),
    retrieve=extend_schema(tags=["Ferry - Accusations"]),
    update=extend_schema(tags=["Ferry - Accusations"]),
    partial_update=extend_schema(tags=["Ferry - Accusations"]),
    create=extend_schema(tags=["Ferry - Accusations"]),
    destroy=extend_schema(tags=["Ferry - Accusations"]),
)
class AccusationViewset(viewsets.ModelViewSet):
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    permission_classes = [permissions.IsAuthenticated, AccusationObjectPermission]
    ordering_fields = ("created_at", "updated_at")
    filterset_fields = ("suspect", "created_by")
    serializer_class = AccusationSerializer

    def get_queryset(self) -> AccusationQuerySet:
        assert self.request.user.is_authenticated
        return Accusation.objects.for_user(self.request.user)

    def create(self, request: Request) -> Response:
        serializer = AccusationCreateSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        accusation = serializer.save()
        response_serializer = AccusationSerializer(accusation)
        return Response(response_serializer.data, status=HTTPStatus.CREATED)

    @extend_schema(tags=["Ferry - Ratifications"])
    @action(
        detail=True, methods=["GET"], permission_classes=[permissions.IsAuthenticated, RatificationObjectPermission]
    )
    def ratification(self, request: Request, pk: None = None) -> Response:
        accusation = self.get_object()
        try:
            serializer = RatificationSerializer(accusation.ratification)
            return Response(serializer.data)
        except Ratification.DoesNotExist:
            return Response({"detail": "Accusation is not ratified."}, status=HTTPStatus.NOT_FOUND)

    @extend_schema(tags=["Ferry - Ratifications"])
    @ratification.mapping.post
    def ratification_create(self, request: Request, pk: None = None) -> Response:
        accusation = self.get_object()
        try:
            _ = accusation.ratification
            return Response({"detail": "Accusation is already ratified."}, status=HTTPStatus.CONFLICT)
        except Ratification.DoesNotExist:
            pass

        context = {"accusation": accusation, **self.get_serializer_context()}
        serializer = RatificationCreateSerializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        ratification = serializer.save()

        response_serializer = RatificationSerializer(ratification)

        return Response(response_serializer.data, status=HTTPStatus.CREATED)

    @extend_schema(tags=["Ferry - Ratifications"])
    @ratification.mapping.delete
    def ratification_delete(self, request: Request, pk: None = None) -> Response:
        accusation = self.get_object()
        try:
            ratification = accusation.ratification
            ratification.delete()
            return Response(status=HTTPStatus.NO_CONTENT)
        except Ratification.DoesNotExist:
            return Response({"detail": "Accusation is not ratified."}, status=HTTPStatus.NOT_FOUND)
