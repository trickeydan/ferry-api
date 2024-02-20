from ninja import Schema

from ferry.court.api.schema import PersonLink


class UserInfo(Schema):
    username: str
    person: PersonLink | None
