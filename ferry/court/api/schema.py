from ninja import ModelSchema

from ferry.court.models import Person


class PersonDetail(ModelSchema):
    class Meta:
        model = Person
        fields = ["id", "display_name", "discord_id", "created_at", "updated_at"]
        extra = "forbid"


class PersonUpdate(ModelSchema):
    display_name: str
    discord_id: int | None

    class Meta:
        model = Person
        fields = ["display_name", "discord_id"]
        fields_optional = "__all__"
        extra = "forbid"
