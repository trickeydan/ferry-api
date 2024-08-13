from typing import Any

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import exceptions, filters, permissions, serializers, viewsets
from rest_framework.request import Request

from ferry.court.models import Person, PersonQuerySet

from .serializers import PersonSerializer


class RulesObjectPermission(permissions.BasePermission):
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


class PersonViewset(
    viewsets.ModelViewSet,
):
    serializer_class = PersonSerializer
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    permission_classes = [permissions.IsAuthenticated, RulesObjectPermission]
    ordering_fields = ("display_name", "current_score", "created_at", "updated_at")
    filterset_fields = ["discord_id"]

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
