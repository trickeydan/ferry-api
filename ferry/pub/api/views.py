from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets

from ferry.pub.api.serializers import PubEventSerializer, PubSerializer
from ferry.pub.models import Pub, PubEvent, PubEventQuerySet, PubQuerySet


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
    destroy=extend_schema(tags=["Pub - Events"]),
)
class PubEventViewset(viewsets.ModelViewSet):
    serializer_class = PubEventSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ("discord_id",)

    def get_queryset(self) -> PubEventQuerySet:
        assert self.request.user.is_authenticated
        return PubEvent.objects.for_user(self.request.user)
