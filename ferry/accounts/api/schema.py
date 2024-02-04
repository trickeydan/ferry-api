from ninja import ModelSchema

from ferry.accounts.models import User


class UserInfo(ModelSchema):
    class Meta:
        model = User
        fields = ["username"]
