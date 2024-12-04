import random
from typing import Any

from rest_framework import exceptions, serializers

from ferry.accounts.api.serializers import PersonLinkSerializer
from ferry.accounts.models import Person
from ferry.court.models import Accusation, Consequence, Ratification


class CurrentPersonDefault:
    """
    May be applied as a `default=...` value on a serializer field.
    Returns the current user.
    """

    requires_context = True

    def __call__(self, serializer_field: serializers.Field) -> Person:
        return serializer_field.context["request"].user.person


class ConsequenceSerializer(serializers.ModelSerializer[Consequence]):
    created_by: serializers.Field = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), default=CurrentPersonDefault()
    )

    class Meta:
        model = Consequence
        fields = ("id", "content", "is_enabled", "created_by", "created_at", "updated_at")

    def validate_created_by(self, value: Person | None) -> Person:
        if not self.context["request"].user.has_perm("court.act_for_person", value):
            raise exceptions.PermissionDenied("You cannot act on behalf of other people.")

        if not value:
            raise exceptions.ValidationError("You must specify a person if no person is associated with your user.")
        return value


class ConsequenceReadSerializer(ConsequenceSerializer):
    created_by = PersonLinkSerializer(read_only=True)


class ConsequenceLinkSerializer(serializers.ModelSerializer[Consequence]):
    class Meta:
        model = Consequence
        fields = ("id", "content")


class RatificationSerializer(serializers.ModelSerializer[Ratification]):
    consequence = ConsequenceLinkSerializer(read_only=True)
    created_by = PersonLinkSerializer(read_only=True)

    class Meta:
        model = Ratification
        fields = ("id", "consequence", "created_by", "created_at", "updated_at")


class RatificationCreateSerializer(serializers.ModelSerializer[Ratification]):
    created_by: serializers.Field = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), default=CurrentPersonDefault()
    )

    class Meta:
        model = Ratification
        fields = ("created_by",)

    def validate_created_by(self, value: Person | None) -> Person:
        if not self.context["request"].user.has_perm("court.act_for_person", value):
            raise exceptions.PermissionDenied("You cannot act on behalf of other people.")

        if not value:
            raise exceptions.ValidationError("You must specify a person if no person is associated with your user.")

        accusation = self.context["accusation"]
        if value == accusation.created_by:
            raise exceptions.ValidationError("You cannot ratify an accusation that you made.")

        if value == accusation.suspect:
            raise exceptions.ValidationError("You cannot ratify an accusation made against you.")

        return value

    def create(self, validated_data: dict[str, Any]) -> Ratification:
        try:
            validated_data["consequence"] = random.choice(Consequence.objects.filter(is_enabled=True).all())  # noqa: S311
        except IndexError:
            raise exceptions.NotAcceptable("No consequences available to assign") from None

        validated_data["accusation"] = self.context["accusation"]
        return super().create(validated_data)


class AccusationCreateSerializer(serializers.ModelSerializer[Accusation]):
    created_by: serializers.Field = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.all(), default=CurrentPersonDefault()
    )
    suspect: serializers.Field = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all())

    class Meta:
        model = Accusation
        fields: tuple[str, ...] = ("id", "quote", "suspect", "created_by", "created_at", "updated_at")

    def validate_created_by(self, value: Person | None) -> Person:
        if not self.context["request"].user.has_perm("court.act_for_person", value):
            raise exceptions.PermissionDenied("You cannot act on behalf of other people.")

        if not value:
            raise exceptions.ValidationError("You must specify a person if no person is associated with your user.")

        return value

    def validate(self, data: dict[str, Any]) -> Any:
        try:
            if data["suspect"] == data["created_by"]:
                raise exceptions.ValidationError("Unable to create accusation that suspects the creator.")
        except KeyError:
            pass
        return super().validate(data)


class AccusationSerializer(AccusationCreateSerializer):
    suspect = PersonLinkSerializer(read_only=True)
    ratification = RatificationSerializer(read_only=True)
    created_by = PersonLinkSerializer(read_only=True)

    class Meta(AccusationCreateSerializer.Meta):
        fields = AccusationCreateSerializer.Meta.fields + ("ratification",)
