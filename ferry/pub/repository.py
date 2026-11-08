from datetime import datetime
from typing import Any

from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from ferry.accounts.models import Person, PersonQuerySet, User
from ferry.pub.forms import PubEventBookingForm
from ferry.pub.models import (
    Pub,
    PubEvent,
    PubEventAttendanceTombstone,
    PubEventQuerySet,
    PubEventRSVP,
    PubEventRSVPMethod,
)


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


def get_listed_pubs(user: User) -> models.QuerySet[Pub]:
    """Active pubs, with the default pub first."""
    return Pub.objects.for_user(user).active().order_by("-is_default", Lower("name"))


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

    # Skipping is part of AutoPub, so it is only on offer to people who have it on.
    if next_event:
        rsvp_method = next_event_rsvp.method if next_event_rsvp else None
        can_skip = rsvp_method == PubEventRSVPMethod.AUTO
        can_undo_skip = rsvp_method == PubEventRSVPMethod.TOMBSTONE
    else:
        can_skip = not has_upcoming_tombstone
        can_undo_skip = has_upcoming_tombstone
    autopub_enabled = bool(person and person.autopub)

    return {
        "can_skip": autopub_enabled and can_skip,
        "can_undo_skip": autopub_enabled and can_undo_skip,
        "next_event": next_event,
        "next_event_rsvp": next_event_rsvp,
        "next_event_attendee_count": next_event_attendee_count,
        "has_upcoming_tombstone": has_upcoming_tombstone,
        "person": person,
    }


def get_pub_stats(*, now: datetime | None = None) -> dict[str, Any]:
    """Events held so far in the current academic year (1 September to 31 August) and their average attendance.

    Events that haven't happened yet are left out, as their attendance isn't final.
    """
    now = timezone.localtime(now or timezone.now())
    start_year = now.year if now.month >= 9 else now.year - 1
    start = datetime(start_year, 9, 1, tzinfo=now.tzinfo)

    events = PubEvent.objects.filter(timestamp__gte=start, timestamp__lte=now)
    event_count = events.count()
    attendances = PubEventRSVP.objects.filter(pub_event__in=events, is_attending=True).count()

    return {
        "academic_year": f"{start_year}/{str(start_year + 1)[-2:]}",
        "event_count": event_count,
        "average_attendees": attendances / event_count if event_count else None,
    }
