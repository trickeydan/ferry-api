from datetime import UTC, datetime
from http import HTTPStatus

import pytest
from django.test import Client
from django.urls import reverse

from ferry.accounts.models import Person, User
from ferry.court.factories import AccusationFactory
from ferry.court.models import Accusation
from ferry.dashboard.services import get_score_sparkline_data


def accuse(suspect: Person, *, year: int, month: int = 10) -> Accusation:
    accusation = AccusationFactory.create(suspect=suspect)
    # created_at is set automatically on creation, so move it into the academic year under test.
    Accusation.objects.filter(pk=accusation.pk).update(created_at=datetime(year, month, 1, tzinfo=UTC))
    return accusation


@pytest.mark.django_db
class TestScoreSparklineData:
    def test_none_without_history(self, person: Person) -> None:
        assert get_score_sparkline_data([person.display_name]) is None

    def test_none_with_a_single_academic_year(self, person: Person) -> None:
        accuse(person, year=2024)

        assert get_score_sparkline_data([person.display_name]) is None

    def test_none_when_nobody_selected_has_history(self, person: Person) -> None:
        accuse(person, year=2023)
        accuse(person, year=2024)

        assert get_score_sparkline_data(["Someone Else"]) is None

    def test_draws_one_line_per_person_on_a_shared_scale(self, person: Person) -> None:
        other = Person.objects.create(display_name="Other Person")
        # person: 1 in 2023/24, 3 in 2024/25. other: 1 in each.
        accuse(person, year=2023)
        for _ in range(3):
            accuse(person, year=2024)
        accuse(other, year=2023)
        accuse(other, year=2024)

        data = get_score_sparkline_data([person.display_name, other.display_name])

        assert data is not None
        assert (data["first_label"], data["last_label"]) == ("2023/24", "2024/25")
        first, second = data["series"]
        assert (first["label"], first["latest"]) == (person.display_name, 3)
        assert (second["label"], second["latest"]) == ("Other Person", 1)
        assert first["color"] != second["color"]
        # The highest value (3) sits at the top padding, so the lower one must sit below it.
        assert first["end_y"] == 4.0
        assert second["end_y"] > first["end_y"]
        # Points run from the left padding to the right padding.
        assert first["points"].startswith("4.0,")
        assert first["points"].endswith(f"{first['end_x']},{first['end_y']}")
        assert first["end_x"] == 236.0

    def test_academic_year_starts_in_september(self, person: Person) -> None:
        accuse(person, year=2024, month=8)  # Still 2023/24.
        accuse(person, year=2024, month=9)  # Starts 2024/25.

        data = get_score_sparkline_data([person.display_name])

        assert data is not None
        assert (data["first_label"], data["last_label"]) == ("2023/24", "2024/25")


@pytest.mark.django_db
class TestFerriesOverviewSparkline:
    url = reverse("dashboard:ferries-overview")

    def test_empty_state(self, client: Client, user_with_person: User) -> None:
        client.force_login(user_with_person)

        response = client.get(self.url)

        assert response.status_code == HTTPStatus.OK
        assert response.context["score_sparkline"] is None
        assert b"Not enough history" in response.content

    def test_renders_chart_and_link_to_full_history(
        self, client: Client, user_with_person: User, person: Person
    ) -> None:
        accuse(person, year=2023)
        accuse(person, year=2024)
        client.force_login(user_with_person)

        content = client.get(self.url).content.decode()

        assert "<polyline" in content
        assert 'role="img"' in content
        assert "2023/24" in content
        assert reverse("dashboard:score-history") in content
