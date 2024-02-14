from datetime import datetime
from uuid import UUID

from ninja import Schema


class PersonLink(Schema):
    id: UUID
    display_name: str


class PersonDetail(Schema):
    id: UUID
    display_name: str
    discord_id: int | None
    current_score: int = 0
    created_at: datetime
    updated_at: datetime


class PersonUpdate(Schema):
    display_name: str
    discord_id: int | None


class ConsequenceLink(Schema):
    id: UUID
    content: str


class ConsequenceDetail(Schema):
    id: UUID
    content: str
    is_enabled: bool
    created_by: PersonLink
    created_at: datetime
    updated_at: datetime


class ConsequenceCreate(Schema):
    content: str
    is_enabled: bool = True
    created_by: UUID


class ConsequenceUpdate(Schema):
    content: str
    is_enabled: bool

    class Meta:
        model = Consequence
        fields = ["content", "is_enabled"]
        extra = "forbid"
