from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import viewsets

from ferry.pub.api.serializers import PubSerializer
from ferry.pub.models import Pub, PubQuerySet


@extend_schema_view(
    list=extend_schema(tags=["Pub - Pubs"]),
    retrieve=extend_schema(tags=["Pub - Pubs"]),
)
class PubViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = PubSerializer

    def get_queryset(self) -> PubQuerySet:
        assert self.request.user.is_authenticated
        return Pub.objects.for_user(self.request.user)
