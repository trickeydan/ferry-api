"""Steps for the consequences and score history features."""

from datetime import UTC, datetime

from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, then, when

from e2e.steps.helpers import person_of
from ferry.accounts.factories import PersonFactory
from ferry.accounts.models import Person, User
from ferry.court.factories import AccusationFactory, ConsequenceFactory
from ferry.court.models import Accusation


@given(parsers.parse('I have a consequence "{content}"'))
def have_consequence(current_user: User, content: str) -> None:
    ConsequenceFactory.create(content=content, created_by=person_of(current_user))


@when("I confirm the dialog")
def confirm_dialog(page: Page) -> None:
    page.locator(".swal2-confirm").click()


@when("I dismiss the dialog")
def dismiss_dialog(page: Page) -> None:
    page.keyboard.press("Escape")


@then("the dialog should be closed")
def dialog_closed(page: Page) -> None:
    expect(page.locator(".swal2-container")).to_have_count(0)


@then(parsers.parse('the consequence "{content}" should be enabled'))
def consequence_enabled(page: Page, content: str) -> None:
    row = page.get_by_role("row", name=content)
    expect(row).to_contain_text("✅")
    expect(row.get_by_role("button", name="Deactivate")).to_be_visible()


@then(parsers.parse('the consequence "{content}" should be disabled'))
def consequence_disabled(page: Page, content: str) -> None:
    row = page.get_by_role("row", name=content)
    expect(row).to_contain_text("❌")
    expect(row.get_by_role("button", name="Deactivate")).to_have_count(0)


@given(parsers.parse('"{name}" has {count:d} ratified accusations from {year:d}'))
def ratified_accusations(name: str, count: int, year: int) -> None:
    person, _ = Person.objects.get_or_create(display_name=name)
    for _ in range(count):
        accusation = AccusationFactory.create(suspect=person)
        # Scores are grouped by the academic year an accusation was made in, which starts in September.
        Accusation.objects.filter(pk=accusation.pk).update(created_at=datetime(year, 10, 1, tzinfo=UTC))


@given("the app has plenty of data")
def plenty_of_data(current_user: User) -> None:
    for name in ("Alice Anderson-Featherstonehaugh", "Bob Brown", "Cat Carter"):
        person = PersonFactory.create(display_name=name)
        AccusationFactory.create_batch(2, suspect=person)
    ConsequenceFactory.create(
        content="Wear the captain's hat to the next three pub nights", created_by=person_of(current_user)
    )


@then(parsers.parse("the chart should have {count:d} lines"))
def chart_lines(page: Page, count: int) -> None:
    page.wait_for_function("() => window.Chart && Chart.getChart('annual-score-chart')")
    assert page.evaluate("Chart.getChart('annual-score-chart').data.datasets.length") == count


@then(parsers.parse('the score table should have the years "{years}"'))
def score_table_years(page: Page, years: str) -> None:
    expect(page.locator("#annual-score-table thead th")).to_have_text(["Person", *years.split(", ")])


@then(parsers.parse('the score table should show "{name}" with {scores}'))
def score_table_row(page: Page, name: str, scores: str) -> None:
    row = page.locator("#annual-score-table tbody tr", has=page.get_by_role("rowheader", name=name))
    expect(row.locator("td")).to_have_text(scores.split(", "))
