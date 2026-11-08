from datetime import UTC, datetime, timedelta
from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse

from ferry.accounts.factories import PersonFactory
from ferry.accounts.models import Person, User
from ferry.conftest import APITest
from ferry.pub.models import Pub, PubEvent, PubEventRSVP, PubEventRSVPMethod

NOW = datetime(2026, 3, 15, 12, tzinfo=UTC)


@pytest.fixture
def events(person: Person) -> list[PubEvent]:
    """Six past events, oldest first, and one in the future at the end."""
    pub = Pub.objects.create(name="The Anchor", emoji="🍺", map_url="https://example.com/map")
    return [
        PubEvent.objects.create(timestamp=NOW + timedelta(weeks=week), pub=pub, created_by=person)
        for week in (*range(-6, 0), 1)
    ]


def rsvp(person: Person, event: PubEvent, *, attending: bool = True, method: str = PubEventRSVPMethod.WEB) -> None:
    PubEventRSVP.objects.create(pub_event=event, person=person, is_attending=attending, method=method)


def streak(person: Person) -> int:
    return Person.objects.with_pub_streak(now=NOW).get(pk=person.pk).pub_streak


@pytest.mark.django_db
class TestPubStreak:
    def test_zero_without_any_events(self, person: Person) -> None:
        assert streak(person) == 0

    def test_zero_without_any_rsvps(self, person: Person, events: list[PubEvent]) -> None:
        assert streak(person) == 0

    def test_attended_every_past_event(self, person: Person, events: list[PubEvent]) -> None:
        for event in events[:6]:
            rsvp(person, event)

        assert streak(person) == 6

    def test_a_missed_event_ends_the_streak(self, person: Person, events: list[PubEvent]) -> None:
        for event in events[:3] + events[4:6]:  # Missed the fourth.
            rsvp(person, event)

        assert streak(person) == 2

    def test_missing_the_latest_event_means_zero(self, person: Person, events: list[PubEvent]) -> None:
        for event in events[:5]:
            rsvp(person, event)

        assert streak(person) == 0

    def test_newcomer_streak_counts_from_first_attendance(self, person: Person, events: list[PubEvent]) -> None:
        for event in events[4:6]:
            rsvp(person, event)

        assert streak(person) == 2

    def test_opting_out_or_being_skipped_breaks_the_streak(self, person: Person, events: list[PubEvent]) -> None:
        for event in events[:4] + events[5:6]:
            rsvp(person, event)
        rsvp(person, events[4], attending=False, method=PubEventRSVPMethod.TOMBSTONE)

        assert streak(person) == 1

    def test_any_attending_method_counts(self, person: Person, events: list[PubEvent]) -> None:
        for event, method in zip(
            events[3:6],
            [PubEventRSVPMethod.AUTO, PubEventRSVPMethod.DISCORD, PubEventRSVPMethod.MANUAL],
            strict=True,
        ):
            rsvp(person, event, method=method)

        assert streak(person) == 3

    def test_future_event_is_not_counted_or_held_against_anyone(self, person: Person, events: list[PubEvent]) -> None:
        for event in events[:6]:
            rsvp(person, event)
        rsvp(person, events[6])  # Attending the future event adds nothing.

        assert streak(person) == 6

    def test_streaks_are_per_person(self, person: Person, events: list[PubEvent]) -> None:
        other = PersonFactory.create()
        for event in events[:6]:
            rsvp(person, event)
        rsvp(other, events[5])

        streaks = {p.pk: p.pub_streak for p in Person.objects.with_pub_streak(now=NOW)}

        assert streaks == {person.pk: 6, other.pk: 1}


@pytest.mark.django_db
class TestPubStreakPages:
    def make_streak(self, person: Person, length: int) -> None:
        pub = Pub.objects.create(name="The Anchor", emoji="🍺", map_url="https://example.com/map")
        now = datetime.now(tz=UTC)
        for week in range(length):
            event = PubEvent.objects.create(timestamp=now - timedelta(weeks=week + 1), pub=pub, created_by=person)
            rsvp(person, event)

    def test_person_list_shows_streak(self, client: Client, user_with_person: User, person: Person) -> None:
        self.make_streak(person, 3)
        client.force_login(user_with_person)

        response = client.get(reverse("accounts:person-list"))

        assert response.status_code == HTTPStatus.OK
        assert b"Pub streak" in response.content
        assert [p.pub_streak for p in response.context["object_list"]] == [3]

    def test_person_page_shows_streak(self, client: Client, user_with_person: User, person: Person) -> None:
        self.make_streak(person, 4)
        client.force_login(user_with_person)

        response = client.get(reverse("accounts:person-detail", args=[person.id]))

        assert response.status_code == HTTPStatus.OK
        assert response.context["object"].pub_streak == 4
        assert b"Pub streak: 4" in response.content


@pytest.mark.django_db
class TestPubStreakNotInApi(APITest):
    def test_people_api_does_not_expose_it(self, client: Client, admin_user: User, person: Person) -> None:
        headers = self.get_headers(admin_user)

        listing = client.get(reverse("api-2.0.0:people-list"), headers=headers).json()["results"][0]
        detail = client.get(reverse("api-2.0.0:people-detail", args=[person.id]), headers=headers).json()

        assert "pub_streak" not in listing
        assert "pub_streak" not in detail
