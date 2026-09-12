from typing import Any

from rest_framework import serializers


class ScoreHistoryDatasetSerializer(serializers.Serializer):
    label: Any = serializers.CharField()
    data: Any = serializers.ListField(child=serializers.IntegerField())


class ScoreHistorySerializer(serializers.Serializer):
    labels = serializers.ListField(child=serializers.CharField())
    datasets = ScoreHistoryDatasetSerializer(many=True)
