from ninja import ModelSchema

from ferry.court.models import Person


class PersonInfo(ModelSchema):
    class Meta:
        model = Person
        fields = ["id", "display_name", "discord_id", "created_at", "updated_at"]
