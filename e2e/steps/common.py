"""Steps shared by every feature."""

import re
from collections.abc import Callable

from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, then, when

from ferry.accounts.models import User


@given("I am signed in as a member", target_fixture="current_user")
def signed_in_member(sign_in: Callable[..., User]) -> User:
    return sign_in()


@given("I am signed in as an admin", target_fixture="current_user")
def signed_in_admin(sign_in: Callable[..., User]) -> User:
    return sign_in(name="Test Admin", is_admin=True)


@given("I am signed in as a member using AutoPub", target_fixture="current_user")
def signed_in_autopub_member(sign_in: Callable[..., User]) -> User:
    return sign_in(autopub=True)


@when(parsers.parse('I open "{path}"'))
def open_path(goto: Callable[[str], None], path: str) -> None:
    goto(path)


@when(parsers.parse('I click the "{name}" link'))
def click_link(page: Page, name: str) -> None:
    page.get_by_role("link", name=name, exact=True).click()


@when(parsers.parse('I click the "{name}" button'))
def click_button(page: Page, name: str) -> None:
    # Some actions are offered in more than one place on a page, such as skipping the next pub.
    page.get_by_role("button", name=name, exact=True).first.click()


@when(parsers.parse('I fill in "{label}" with "{value}"'))
def fill_in(page: Page, label: str, value: str) -> None:
    page.get_by_role("textbox", name=label).fill(value)


@when("I reload the page")
def reload_page(page: Page) -> None:
    page.reload()


@when("I note that the page has not reloaded yet")
def note_page(page: Page) -> None:
    page.evaluate("window.__notReloaded = true")


@then("the page should not have reloaded")
def page_not_reloaded(page: Page) -> None:
    assert page.evaluate("window.__notReloaded === true"), "The page was reloaded, so it was not updated in place."


@then("there should be no JavaScript errors")
def no_js_errors(js_errors: list[str]) -> None:
    assert js_errors == []


@then(parsers.parse('I should be on "{path}"'))
def should_be_on(page: Page, path: str) -> None:
    expect(page).to_have_url(re.compile(rf"^https?://[^/]+{re.escape(path)}(\?.*)?$"))


@then(parsers.parse('I should see "{text}"'))
def should_see(page: Page, text: str) -> None:
    expect(page.get_by_text(text).first).to_be_visible()


@then(parsers.parse('I should not see "{text}"'))
def should_not_see(page: Page, text: str) -> None:
    expect(page.get_by_text(text)).to_have_count(0)


@then(parsers.parse('I should see a "{name}" button'))
def should_see_button(page: Page, name: str) -> None:
    expect(page.get_by_role("button", name=name, exact=True).first).to_be_visible()


@then(parsers.parse('I should not see a "{name}" button'))
def should_not_see_button(page: Page, name: str) -> None:
    expect(page.get_by_role("button", name=name, exact=True)).to_have_count(0)


@then(parsers.parse('the "{name}" tab should be active'))
def tab_is_active(page: Page, name: str) -> None:
    expect(page.locator(".nav-tabs .nav-link.active")).to_have_text(name)
