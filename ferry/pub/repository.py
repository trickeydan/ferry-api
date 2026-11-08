from typing import Any

from django.db import models
from django.db.models.functions import Lower

from ferry.accounts.models import Person, PersonQuerySet
from ferry.pub.forms import PubEventBookingForm
from ferry.pub.models import PubEvent, PubEventAttendanceTombstone, PubEventQuerySet, PubEventRSVP


def get_attendees_for_pub_event(pub_event: PubEvent) -> PersonQuerySet:
    person_ids = pub_event.pub_event_rsvps.filter(is_attending=True).values("person")
    return Person.objects.filter(id__in=person_ids).order_by(Lower("display_name"))


def get_attendance_tombstones_for_pub_event(pub_event: PubEvent) -> PersonQuerySet:
    person_ids = pub_event.attendance_tombstones.values("person")
    return Person.objects.filter(id__in=person_ids).order_by(Lower("display_name"))


def annotate_attendee_count(pub_event_qs: PubEventQuerySet) -> PubEventQuerySet:
    sub_qs = (
        PubEventRSVP.objects.filter(pub_event_id=models.OuterRef("id"), is_attending=True)
        .order_by()
        .annotate(count=models.Func(models.F("id"), function="Count"))
        .values("count")
    )
    return pub_event_qs.annotate(attendee_count=models.Subquery(sub_qs, output_field=models.IntegerField()))


def get_pub_booking_form(pub_event: PubEvent, *, data: Any | None = None) -> PubEventBookingForm:
    return PubEventBookingForm(data=data, pub_event=pub_event)


def get_next_pub_summary(person: Person | None) -> dict[str, Any]:
    """Context for the next-pub card shown on the home and pub landing pages."""
    next_event = PubEvent.objects.get_next()
    next_event_rsvp = None
    next_event_attendee_count = None
    has_upcoming_tombstone = False

    if next_event:
        next_event_attendee_count = get_attendees_for_pub_event(next_event).count()
        if person:
            next_event_rsvp = PubEventRSVP.objects.filter(pub_event=next_event, person=person).first()
    elif person:
        has_upcoming_tombstone = PubEventAttendanceTombstone.objects.filter(
            person=person, pub_event__isnull=True
        ).exists()

    return {
        "next_event": next_event,
        "next_event_rsvp": next_event_rsvp,
        "next_event_attendee_count": next_event_attendee_count,
        "has_upcoming_tombstone": has_upcoming_tombstone,
        "person": person,
    }
