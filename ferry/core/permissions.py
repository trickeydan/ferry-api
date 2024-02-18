from __future__ import annotations

import rules

from ferry.accounts.models import User
from ferry.court.models import Consequence, Person


@rules.predicate  # type: ignore[misc]
def user_is_person(user: User, person: Person) -> bool:
    try:
        return user.person == person
    except Person.DoesNotExist:
        return False


@rules.predicate  # type: ignore[misc]
def user_created_consequence(user: User, consequence: Consequence) -> bool:
    try:
        return user.person == consequence.created_by
    except Person.DoesNotExist:
        return False


# Consequences

rules.add_perm("court.view_consequence", user_created_consequence | rules.is_superuser)
rules.add_perm("court.create_consequence", rules.always_allow)
rules.add_perm("court.edit_consequence", rules.is_superuser)
rules.add_perm("court.delete_consequence", rules.is_superuser)

# # People

rules.add_perm("court.act_on_behalf_of_person", user_is_person | rules.is_superuser)

rules.add_perm("court.view_person", rules.always_allow)
rules.add_perm("court.create_person", rules.is_superuser)
rules.add_perm("court.edit_person", user_is_person | rules.is_superuser)
rules.add_perm("court.delete_person", rules.is_superuser)
