from django.http import HttpRequest
from ninja import Router

from ferry.accounts.models import User

from .schema import UserInfo

router = Router()


@router.get("/me", response=UserInfo, summary="Get the current user", tags=["Users"])
def users_me(request: HttpRequest) -> User:
    assert request.user.is_authenticated
    return request.user
