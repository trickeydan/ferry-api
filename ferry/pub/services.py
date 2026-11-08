from django.db import models, transaction

from ferry.accounts.models import Person
from ferry.pub.models import PubEvent, PubEventAttendanceTombstone, PubEventRSVP, PubEventRSVPMethod


class TombstoneAlreadyExistsError(Exception):
    pass


def _tombstones_for_next_pub(
    person: Person, pub_event: PubEvent | None
) -> models.QuerySet[PubEventAttendanceTombstone]:
    qs = PubEventAttendanceTombstone.objects.filter(person=person)
    return qs.filter(pub_event=pub_event) if pub_event else qs.filter(pub_event__isnull=True)


def skip_next_pub(person: Person) -> PubEventAttendanceTombstone:
    """Skip the next pub, even if it hasn't been created yet."""
    with transaction.atomic():
        # If there is a next pub event, the tombstone is linked to it straight away.
        pub_event = PubEvent.objects.get_next()

        if _tombstones_for_next_pub(person, pub_event).exists():
            raise TombstoneAlreadyExistsError

        tombstone = PubEventAttendanceTombstone.objects.create(pub_event=pub_event, person=person)

        # Update any RSVPs using AutoPub for the event, if it exists.
        if pub_event:
            PubEventRSVP.objects.filter(pub_event=pub_event, person=person, method=PubEventRSVPMethod.AUTO).update(
                method=PubEventRSVPMethod.TOMBSTONE, is_attending=False
            )

    return tombstone


def undo_skip_next_pub(person: Person) -> bool:
    """Remove a skip for the next pub. Returns whether there was a skip to remove."""
    with transaction.atomic():
        pub_event = PubEvent.objects.get_next()

        deleted, _ = _tombstones_for_next_pub(person, pub_event).delete()

        if pub_event:
            PubEventRSVP.objects.filter(pub_event=pub_event, person=person, method=PubEventRSVPMethod.TOMBSTONE).update(
                method=PubEventRSVPMethod.AUTO, is_attending=True
            )

    return deleted > 0


def set_autopub(person: Person, *, enabled: bool) -> None:
    with transaction.atomic():
        person.autopub = enabled
        person.save(update_fields=["autopub"])

        # A pending skip only means something while AutoPub is on, so don't leave a stale one behind.
        if not enabled:
            PubEventAttendanceTombstone.objects.filter(person=person, pub_event__isnull=True).delete()
