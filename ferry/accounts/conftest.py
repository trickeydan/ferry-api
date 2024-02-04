import pytest

from .models import APIToken, User


@pytest.fixture
def user() -> User:
    return User.objects.create(username="user")


@pytest.fixture
def api_token(user: User) -> APIToken:
    return user.api_tokens.create(is_active=True)
