# mypy: disable-error-code="no-untyped-call"
from __future__ import annotations

import rules

from ferry.accounts.models import Person, User
from ferry.court.models import Consequence


@rules.predicate  # type: ignore[misc]
def user_created_consequence(user: User, consequence: Consequence) -> bool:
    try:
        return user.person == consequence.created_by
    except Person.DoesNotExist:
        return False


@rules.predicate  # type: ignore[misc]
def user_is_person(user: User, person: Person) -> bool:
    try:
        return user.person == person
    except Person.DoesNotExist:
        return False


# Global

# Act on behalf of a person
rules.add_perm("court.act_for_person", user_is_person | rules.is_superuser)

# Accusations

rules.add_perm("court.view_accusation", rules.always_allow)
rules.add_perm("court.create_accusation", rules.always_allow)
rules.add_perm("court.edit_accusation", rules.is_superuser)
rules.add_perm("court.delete_accusation", rules.is_superuser)

# Consequences

rules.add_perm("court.view_consequence", user_created_consequence | rules.is_superuser)
rules.add_perm("court.create_consequence", rules.always_allow)
rules.add_perm("court.edit_consequence", rules.is_superuser)
rules.add_perm("court.delete_consequence", rules.is_superuser)

# People

rules.add_perm("court.view_person", rules.always_allow)
rules.add_perm("court.create_person", rules.is_superuser)
rules.add_perm("court.edit_person", user_is_person | rules.is_superuser)
rules.add_perm("court.delete_person", rules.is_superuser)

# Trust as a source of verified Discord IDs
rules.add_perm("court.assign_discord_id_to_person", rules.is_superuser)

# Ratifications

rules.add_perm("court.view_ratification", rules.always_allow)
rules.add_perm("court.create_ratification", rules.always_allow)
rules.add_perm("court.delete_ratification", rules.is_superuser)

# Pub Events

rules.add_perm("pub.view_event", rules.always_allow)
rules.add_perm("pub.create_event", rules.is_superuser)
rules.add_perm("pub.edit_event", rules.is_superuser)
rules.add_perm("pub.delete_event", rules.is_superuser)
rules.add_perm("pub.record_attendance", rules.is_superuser)
