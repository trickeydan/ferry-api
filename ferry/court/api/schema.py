from datetime import datetime
from typing import Literal
from uuid import UUID

from ninja import ModelSchema
from pydantic import BaseModel

from ferry.court.models import Consequence, Person


class DeleteConfirmation(BaseModel):
    success: Literal[True] = True


class PersonLink(ModelSchema):
    class Meta:
        model = Person
        fields = ["id", "display_name"]
        extra = "forbid"


class PersonDetail(ModelSchema):
    id: UUID
    display_name: str
    discord_id: int | None
    current_score: int
    created_at: datetime
    updated_at: datetime

    class Meta:
        model = Person
        fields = ["id", "display_name", "discord_id", "created_at", "updated_at"]
        custom_fields = [("current_score", int, 0)]
        extra = "forbid"


class PersonUpdate(ModelSchema):
    display_name: str
    discord_id: int | None

    class Meta:
        model = Person
        fields = ["display_name", "discord_id"]
        fields_optional = "__all__"
        extra = "forbid"


class ConsequenceDetail(ModelSchema):
    id: UUID
    content: str
    is_enabled: bool
    created_by: PersonLink
    created_at: datetime
    updated_at: datetime

    class Meta:
        model = Consequence
        fields = ["id", "content", "is_enabled", "created_by", "created_at", "updated_at"]
        extra = "forbid"
