import pytest


@pytest.fixture(autouse=True)
def _browser_ready() -> None:
    """These tests exercise the report generator and don't need the browser the other e2e tests start."""
