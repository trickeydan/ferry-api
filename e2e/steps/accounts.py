"""Steps for the profile and API token features."""

from playwright.sync_api import Page, expect
from pytest_bdd import given, parsers, then

from ferry.accounts.models import User


@given(parsers.parse('I have an API token called "{name}"'))
def have_api_token(current_user: User, name: str) -> None:
    current_user.api_tokens.create(name=name, is_active=True)


@then(parsers.parse('the API token "{name}" should be active'))
def token_active(page: Page, name: str) -> None:
    row = page.get_by_role("row", name=name)
    expect(row).to_contain_text("✅")
    expect(row.get_by_role("button", name="Deactivate")).to_be_visible()


@then(parsers.parse('the API token "{name}" should be inactive'))
def token_inactive(page: Page, name: str) -> None:
    row = page.get_by_role("row", name=name)
    expect(row).to_contain_text("❌")
    expect(row.get_by_role("button", name="Reactivate")).to_be_visible()
