import pytest

from ferry.accounts.models import User
from ferry.court.factories import PersonFactory
from ferry.court.models import Person


@pytest.fixture
def person() -> Person:
    return PersonFactory()


@pytest.fixture
def user_with_person(person: Person) -> User:
    return User.objects.create(username="user_with_person", person=person)


@pytest.fixture
def admin_user() -> User:
    return User.objects.create(username="admin", is_superuser=True)
