from django.db import models

from ferry.accounts.models import Person, PersonQuerySet
from ferry.pub.models import PubEvent, PubEventQuerySet, PubEventRSVP


def get_attendees_for_pub_event(pub_event: PubEvent) -> PersonQuerySet:
    person_ids = pub_event.pub_event_rsvps.filter(is_attending=True).values("person")
    return Person.objects.filter(id__in=person_ids)


def annotate_attendee_count(pub_event_qs: PubEventQuerySet) -> PubEventQuerySet:
    sub_qs = (
        PubEventRSVP.objects.filter(pub_event_id=models.OuterRef("id"))
        .order_by()
        .annotate(count=models.Func(models.F("id"), function="Count"))
        .values("count")
    )
    return pub_event_qs.annotate(attendee_count=models.Subquery(sub_qs, output_field=models.IntegerField()))
