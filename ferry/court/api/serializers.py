from django.conf import settings
from rest_framework import serializers

from ferry.core.discord import NoSuchGuildMemberError, get_discord_client
from ferry.court.models import Person


class PersonLinkSerializer(serializers.ModelSerializer[Person]):
    class Meta:
        model = Person
        fields = ("id", "display_name")


class PersonSerializer(serializers.ModelSerializer[Person]):
    discord_id = serializers.IntegerField(allow_null=True, required=False)
    current_score = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)

    class Meta:
        model = Person
        fields = ("id", "display_name", "discord_id", "current_score", "created_at", "updated_at")

    def validate_discord_id(self, value: int | None) -> int | None:
        if value:
            discord_client = get_discord_client()
            try:
                discord_client.get_guild_member_by_id(settings.DISCORD_GUILD, value)
            except NoSuchGuildMemberError:
                raise serializers.ValidationError("Unknown discord ID. Is the user part of the guild?") from None
        return value
