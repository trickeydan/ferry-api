from datetime import UTC, datetime
from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse

from ferry.accounts.models import Person, User
from ferry.court.factories import PersonFactory
from ferry.pub.models import Pub, PubEvent, PubEventRSVP, PubEventRSVPMethod
from ferry.pub.repository import get_pub_stats

NOW = datetime(2026, 3, 15, 12, tzinfo=UTC)


def make_event(person: Person, when: datetime, *, attendees: int = 0) -> PubEvent:
    pub, _ = Pub.objects.get_or_create(name="The Anchor", defaults={"emoji": "🍺", "map_url": "https://example.com/m"})
    event = PubEvent.objects.create(timestamp=when, pub=pub, created_by=person)
    for _ in range(attendees):
        PubEventRSVP.objects.create(
            pub_event=event, person=PersonFactory.create(), is_attending=True, method=PubEventRSVPMethod.WEB
        )
    return event


@pytest.mark.django_db
class TestPubStats:
    def test_no_events(self) -> None:
        stats = get_pub_stats(now=NOW)

        assert stats == {"academic_year": "2025/26", "event_count": 0, "average_attendees": None}

    def test_counts_events_and_averages_attendance(self, person: Person) -> None:
        make_event(person, datetime(2025, 10, 2, tzinfo=UTC), attendees=4)
        make_event(person, datetime(2026, 2, 5, tzinfo=UTC), attendees=7)
        make_event(person, datetime(2026, 3, 1, tzinfo=UTC), attendees=0)

        stats = get_pub_stats(now=NOW)

        assert stats["event_count"] == 3
        assert stats["average_attendees"] == pytest.approx(11 / 3)

    def test_only_counts_people_who_are_attending(self, person: Person) -> None:
        event = make_event(person, datetime(2026, 2, 5, tzinfo=UTC), attendees=2)
        PubEventRSVP.objects.create(
            pub_event=event, person=PersonFactory.create(), is_attending=False, method=PubEventRSVPMethod.WEB
        )

        assert get_pub_stats(now=NOW)["average_attendees"] == 2

    def test_academic_year_runs_september_to_august(self, person: Person) -> None:
        make_event(person, datetime(2025, 8, 30, tzinfo=UTC))  # Last year.
        make_event(person, datetime(2025, 9, 2, tzinfo=UTC))  # This year.

        assert get_pub_stats(now=NOW)["event_count"] == 1

    def test_year_label_rolls_over_in_september(self) -> None:
        assert get_pub_stats(now=datetime(2026, 8, 31, tzinfo=UTC))["academic_year"] == "2025/26"
        assert get_pub_stats(now=datetime(2026, 9, 2, tzinfo=UTC))["academic_year"] == "2026/27"

    def test_ignores_events_that_have_not_happened(self, person: Person) -> None:
        make_event(person, datetime(2026, 3, 20, tzinfo=UTC), attendees=5)

        assert get_pub_stats(now=NOW)["event_count"] == 0


@pytest.mark.django_db
class TestHomeStatsCard:
    url = reverse("dashboard:home")

    def test_empty_state_shows_dash(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        response = client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["pub_stats"]["event_count"] == 0
        assert b"events this academic year" in response.content
        assert b"&ndash;" in response.content or "–".encode() in response.content

    def test_shows_stats(self, client: Client, user_with_person: User) -> None:
        stats = {"academic_year": "2025/26", "event_count": 7, "average_attendees": 11 / 3}
        client.force_login(user_with_person)

        with patch("ferry.dashboard.views.get_pub_stats", return_value=stats):
            content = client.get(self.url).content.decode()

        assert "Pub &middot; 2025/26" in content or "Pub · 2025/26" in content
        assert ">7<" in content
        assert ">3.7<" in content
