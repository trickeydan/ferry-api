from rest_framework import serializers

from ferry.pub.models import Pub, PubEvent


class PubSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pub
        fields = ("id", "name", "emoji", "map_url", "menu_url")


class PubEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PubEvent
        fields = (
            "id",
            "timestamp",
            "pub",
            "discord_id",
            "table",
            "attendees",
            "created_by",
            "created_at",
            "updated_at",
        )
