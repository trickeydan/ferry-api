from django.http import HttpRequest
from ninja import Router

from ferry.accounts.models import User
from ferry.api_legacy.schema.core import ErrorDetail
from ferry.api_legacy.schema.users import UserInfo

router = Router()


@router.get("/me", response={200: UserInfo, 401: ErrorDetail}, summary="Get the current user", tags=["Users"])
def users_me(request: HttpRequest) -> User:
    assert request.user.is_authenticated
    return request.user
