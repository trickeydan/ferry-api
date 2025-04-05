import pytest

from ferry.accounts.models import Person, User
from ferry.court.factories import PersonFactory


@pytest.fixture
def person() -> Person:
    return PersonFactory()  # type: ignore[return-value]


@pytest.fixture
def user_with_person(person: Person) -> User:
    return User.objects.create(username="user_with_person", person=person)


@pytest.fixture
def user() -> User:
    return User.objects.create(username="user")


@pytest.fixture
def admin_user() -> User:
    return User.objects.create(username="admin", is_superuser=True)


class APITest:
    def get_headers(self, user: User) -> dict[str, str]:
        api_token = user.api_tokens.create(is_active=True)
        return {
            "Authorization": f"Bearer {api_token.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
