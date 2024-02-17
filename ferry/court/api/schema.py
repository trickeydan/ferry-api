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
    current_score: float
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


class RatificationDetail(Schema):
    id: UUID
    consequence: ConsequenceLink
    created_by: PersonLink
    created_at: datetime
    updated_at: datetime


class RatificationCreate(Schema):
    created_by: UUID


class AccusationCreate(Schema):
    quote: str
    suspect: UUID
    created_by: UUID


class AccusationUpdate(Schema):
    quote: str


class AccusationDetail(Schema):
    id: UUID
    quote: str
    suspect: PersonLink
    ratification: RatificationDetail | None = None
    created_by: PersonLink
    created_at: datetime
    updated_at: datetime
