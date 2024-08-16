from django.conf import settings
from rest_framework import exceptions, serializers

from ferry.core.discord import NoSuchGuildMemberError, get_discord_client
from ferry.court.models import Consequence, Person


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


class CurrentPersonDefault:
    """
    May be applied as a `default=...` value on a serializer field.
    Returns the current user.
    """

    requires_context = True

    def __call__(self, serializer_field: serializers.Field) -> Person:
        return serializer_field.context["request"].user.person  # TODO


class ConsequenceSerializer(serializers.ModelSerializer[Consequence]):
    created_by = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all(), default=CurrentPersonDefault())

    class Meta:
        model = Consequence
        fields = ("id", "content", "is_enabled", "created_by", "created_at", "updated_at")

    def validate_created_by(self, value: Person | None) -> Person:
        if not self.context["request"].user.has_perm("court.act_for_person", value):
            raise exceptions.PermissionDenied("You cannot act on behalf of other people.")

        if not value:
            raise exceptions.ValidationError("You must specify a person if no person is asssociated with your user.")
        return value


class ConsequenceReadSerializer(ConsequenceSerializer):
    created_by = PersonLinkSerializer(read_only=True)  # type: ignore[assignment]
