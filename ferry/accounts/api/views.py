import base64
from typing import Any

from django.core.signing import TimestampSigner
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import exceptions, filters, permissions, renderers, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings

from ferry.accounts.models import Person, PersonQuerySet, User

from .serializers import (
    DiscordLinkTokenSerializer,
    PersonSerializer,
    UserSerializer,
)


class UserViewset(viewsets.GenericViewSet):
    serializer_class = UserSerializer

    @extend_schema(tags=["Users"], description="Get the current user")
    @action(detail=False)
    def me(self, request: Request) -> Response:
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


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


class DiscordJSONRenderer(renderers.JSONRenderer):
    media_type = "application/json; format=discord"
    ferry_format = "discord"


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
    renderer_classes = [DiscordJSONRenderer] + api_settings.DEFAULT_RENDERER_CLASSES  # type: ignore
    ordering_fields = ("display_name", "current_score", "created_at", "updated_at")
    filterset_fields = ("discord_id",)

    def get_serializer_context(self) -> dict[str, Any]:
        return {
            **super().get_serializer_context(),
            "ferry_format": getattr(self.request.accepted_renderer, "ferry_format", "emoji"),
        }

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
