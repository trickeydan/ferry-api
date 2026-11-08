"""Steps for checking the layout on a phone."""

from playwright.sync_api import Page, ViewportSize, expect
from pytest_bdd import given, then, when

PHONE: ViewportSize = {"width": 390, "height": 844}


@given("I am using a phone")
def using_a_phone(page: Page) -> None:
    page.set_viewport_size(PHONE)


@given("I am using a phone with large text")
def using_a_phone_with_large_text(page: Page) -> None:
    """Text is wider on some machines, such as Linux in CI, so check that pages still fit when it is larger."""
    page.set_viewport_size(PHONE)
    page.add_init_script(
        "document.addEventListener('DOMContentLoaded', () => { document.documentElement.style.fontSize = '19px' })"
    )


@when("I open the menu")
def open_menu(page: Page) -> None:
    page.get_by_role("button", name="Toggle navigation").click()


@then("the menu should be collapsed")
def menu_collapsed(page: Page) -> None:
    expect(page.get_by_role("link", name="Ferries", exact=True)).to_be_hidden()
    expect(page.get_by_role("button", name="Toggle navigation")).to_be_visible()


@then("the page should not scroll sideways")
def no_sideways_scroll(page: Page) -> None:
    widths = page.evaluate("({page: document.documentElement.scrollWidth, window: window.innerWidth})")
    assert widths["page"] <= widths["window"], f"The page is {widths['page']}px wide on a {widths['window']}px screen."
