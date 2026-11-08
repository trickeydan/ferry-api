"""Steps for the light and dark theme switcher."""

from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, then, when


@given(parsers.parse("my system is set to a {scheme} theme"))
def system_theme_given(page: Page, scheme: str) -> None:
    page.emulate_media(color_scheme=scheme)  # type: ignore[arg-type]


@when(parsers.parse("my system changes to a {scheme} theme"))
def system_theme_changes(page: Page, scheme: str) -> None:
    page.emulate_media(color_scheme=scheme)  # type: ignore[arg-type]


@when(parsers.parse('I choose the "{theme}" theme'))
def choose_theme(page: Page, theme: str) -> None:
    page.locator("#ferry-theme").click()
    # The menu items have an icon glyph in their accessible names, so find them by their theme value instead.
    page.locator(f'[data-bs-theme-value="{theme.lower()}"]').click()


@then(parsers.parse("the page should use the {theme} theme"))
def page_theme(page: Page, theme: str) -> None:
    expect(page.locator("html")).to_have_attribute("data-bs-theme", theme)
