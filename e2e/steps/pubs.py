"""Steps for the pubs list and add-a-pub features."""

from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, then, when

from ferry.pub.models import Pub


@given(parsers.parse('there is a pub called "{name}"'))
def pub_exists(name: str) -> Pub:
    return Pub.objects.create(name=name, emoji="🍺", map_url="https://example.com/map")


@given(parsers.parse('"{name}" is the default pub'))
def pub_is_default(name: str) -> None:
    pub = Pub.objects.get(name=name)
    pub.is_default = True
    pub.save()


@when(parsers.parse('I pick the "{search}" emoji'))
def pick_emoji(page: Page, search: str) -> None:
    page.locator(".dep-button").click()
    page.locator(".emoji-mart-search input").fill(search)
    # The picker lists emoji from every section, so only take one from the search results.
    page.locator(".emoji-mart-category", has_text="Search Results").locator(".emoji-mart-emoji").first.click()
    expect(page.get_by_role("textbox", name="Emoji")).not_to_have_value("")


@when(parsers.parse('I make "{name}" the default pub'))
def make_default(page: Page, name: str) -> None:
    page.get_by_role("row", name=name).get_by_role("button", name="Make default").click()


@then(parsers.parse('"{name}" should be the default pub'))
def is_default_in_table(page: Page, name: str) -> None:
    expect(page.get_by_role("row", name=name).locator(".badge")).to_have_text("Default")
    expect(page.locator("#pubs-table .badge")).to_have_count(1)


@then(parsers.parse('"{name}" should not be the default pub'))
def is_not_default_in_table(page: Page, name: str) -> None:
    expect(page.get_by_role("row", name=name).locator(".badge")).to_have_count(0)


@then(parsers.parse('the pub "{name}" should have an emoji'))
def pub_has_emoji(name: str) -> None:
    assert Pub.objects.get(name=name).emoji
