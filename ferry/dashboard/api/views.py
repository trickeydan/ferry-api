from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ferry.dashboard.services import get_annual_score_chart_data

from .serializers import ScoreHistorySerializer


class ScoreHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=["Dashboard"],
        responses={200: ScoreHistorySerializer},
        description="Scores earned by each person for each September-to-August academic year.",
    )
    def get(self, request: Request) -> Response:
        serializer = ScoreHistorySerializer(get_annual_score_chart_data())
        return Response(serializer.data)
