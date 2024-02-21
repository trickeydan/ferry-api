from ninja import Schema

from ferry.api.schema.court import PersonLink


class UserInfo(Schema):
    username: str
    person: PersonLink | None
