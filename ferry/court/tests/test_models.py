import pytest
import time_machine

from ferry.court.factories import AccusationFactory, PersonFactory
from ferry.court.models import Person, Ratification


@pytest.mark.django_db
class TestPersonModelWithCurrentScore:
    @pytest.fixture
    def person_1(self) -> Person:
        return PersonFactory()

    def test_no_accusations(self, person_1: Person) -> None:
        person = Person.objects.with_current_score().get(id=person_1.id)

        assert person.current_score == 0  # type: ignore[attr-defined]

    def test_one_accusation(self, person_1: Person) -> None:
        AccusationFactory.create(suspect=person_1)

        person = Person.objects.with_current_score().get(id=person_1.id)

        assert person.current_score == 1  # type: ignore[attr-defined]

    def test_two_accusations(self, person_1: Person) -> None:
        AccusationFactory.create(suspect=person_1)
        AccusationFactory.create(suspect=person_1)

        person = Person.objects.with_current_score().get(id=person_1.id)

        assert person.current_score == 2  # type: ignore[attr-defined]

    def test_ignore_unratified_accusations(self, person_1: Person) -> None:
        AccusationFactory.create(suspect=person_1, ratification=None)

        person = Person.objects.with_current_score().get(id=person_1.id)

        assert person.current_score == 0  # type: ignore[attr-defined]

    @pytest.mark.parametrize(
        ("accusation_time", "expected_score"),
        [
            pytest.param("2023-12-01T12:00:00Z", 1, id="future"),
            pytest.param("2022-12-01T12:00:00Z", 1, id="current-year"),
            pytest.param("2022-09-21T00:00:00Z", 1, id="last-year-but-same-academic"),
            pytest.param("2022-09-01T00:00:00Z", 1, id="boundary-1-later"),
            pytest.param("2022-08-31T23:59:59+01:00", 0.75, id="boundary-1-earlier"),
            pytest.param("2022-08-01T12:00:00Z", 0.75, id="last-year"),
            pytest.param("2021-08-01T12:00:00Z", 0.5, id="two-years"),
            pytest.param("2020-08-01T12:00:00Z", 0.25, id="three-years"),
            pytest.param("2019-08-01T12:00:00Z", 0, id="four-years"),
            pytest.param("2010-08-01T12:00:00Z", 0, id="distant-past"),
        ],
    )
    @time_machine.travel("2023-01-01T00:00:00Z")
    def test_depreciation(self, accusation_time: str, expected_score: int | float, person_1: Person) -> None:
        acc = AccusationFactory.create(suspect=person_1)
        acc.created_at = accusation_time
        acc.save()

        person = Person.objects.with_current_score().get(id=person_1.id)
        assert person.current_score == expected_score  # type: ignore[attr-defined]


@pytest.mark.django_db
class TestRatificationWithScoreValue:
    @pytest.mark.parametrize(
        ("accusation_time", "expected_score"),
        [
            pytest.param("2023-12-01T12:00:00Z", 1, id="future"),
            pytest.param("2022-12-01T12:00:00Z", 1, id="current-year"),
            pytest.param("2022-09-21T00:00:00Z", 1, id="last-year-but-same-academic"),
            pytest.param("2022-09-01T00:00:00Z", 1, id="boundary-1-later"),
            pytest.param("2022-08-31T23:59:59+01:00", 0.75, id="boundary-1-earlier"),
            pytest.param("2022-08-01T12:00:00Z", 0.75, id="last-year"),
            pytest.param("2021-08-01T12:00:00Z", 0.5, id="two-years"),
            pytest.param("2020-08-01T12:00:00Z", 0.25, id="three-years"),
            pytest.param("2019-08-01T12:00:00Z", 0, id="four-years"),
            pytest.param("2010-08-01T12:00:00Z", 0, id="distant-past"),
        ],
    )
    @time_machine.travel("2023-01-01T00:00:00Z")
    def test_depreciation(self, accusation_time: str, expected_score: int | float) -> None:
        acc = AccusationFactory()
        acc.created_at = accusation_time
        acc.save()

        ratification = Ratification.objects.with_score_value().get(id=acc.ratification.id)
        assert ratification.score_value == expected_score
