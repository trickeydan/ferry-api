"""Small helpers for the step definitions."""

from ferry.accounts.models import Person, User


def person_of(user: User) -> Person:
    assert user.person
    return user.person
