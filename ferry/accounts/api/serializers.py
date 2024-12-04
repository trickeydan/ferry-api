import math

from django.conf import settings
from rest_framework import serializers

from ferry.accounts.models import Person, User
from ferry.accounts.repository import ferrify
from ferry.core.discord import NoSuchGuildMemberError, get_discord_client


class DiscordLinkTokenSerializer(serializers.Serializer):
    link_token = serializers.CharField(required=False)


class PersonLinkSerializer(serializers.ModelSerializer[Person]):
    class Meta:
        model = Person
        fields: tuple[str, ...] = ("id", "display_name")


class PersonLinkWithDiscordIdSerializer(serializers.ModelSerializer[Person]):
    class Meta(PersonLinkSerializer.Meta):
        model = Person
        fields = PersonLinkSerializer.Meta.fields + ("discord_id",)


class PersonSerializer(serializers.ModelSerializer[Person]):
    discord_id = serializers.IntegerField(allow_null=True, required=False)
    current_score = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    ferry_sequence = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Person
        fields = ("id", "display_name", "discord_id", "current_score", "ferry_sequence", "created_at", "updated_at")

    def validate_discord_id(self, value: int | None) -> int | None:
        if value:
            discord_client = get_discord_client()
            try:
                discord_client.get_guild_member_by_id(settings.DISCORD_GUILD, value)
            except NoSuchGuildMemberError:
                raise serializers.ValidationError("Unknown discord ID. Is the user part of the guild?") from None
        return value

    def get_ferry_sequence(self, person: Person) -> str:
        if not hasattr(person, "current_score"):
            return ""
        fmt = self.context.get("ferry_format", "emoji")
        return ferrify(math.ceil(person.current_score), seed=person.id.int, fmt=fmt)


class UserSerializer(serializers.ModelSerializer[User]):
    person = PersonLinkSerializer()

    class Meta:
        model = User
        fields = ("username", "person")
