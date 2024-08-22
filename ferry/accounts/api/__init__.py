from drf_spectacular.utils import extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from .serializers import UserSerializer


class UserViewset(viewsets.GenericViewSet):
    serializer_class = UserSerializer

    @extend_schema(tags=["Users"], description="Get the current user")
    @action(detail=False)
    def me(self, request: Request) -> Response:
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
