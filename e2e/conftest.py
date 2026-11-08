"""Browser tests: pytest-bdd scenarios driven through Playwright against a live Django server.

Run them with `make e2e`. They need a Playwright browser (`uv run playwright install chromium`) and network access,
as the pages load Bootstrap, htmx and the emoji picker's images from CDNs.
"""

import hashlib
import json
import shutil
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.test import Client
from playwright.sync_api import BrowserContext, Page
from playwright.sync_api import Error as PlaywrightError
from pytest_bdd.parser import Feature, Scenario, Step
from pytest_django.live_server_helper import LiveServer

from ferry.accounts.factories import PersonFactory
from ferry.accounts.models import User

pytest_plugins = [
    "e2e.steps.common",
    "e2e.steps.accounts",
    "e2e.steps.ferries",
    "e2e.steps.layout",
    "e2e.steps.pub",
    "e2e.steps.pubs",
    "e2e.steps.theme",
]


@pytest.fixture
def js_errors(page: Page) -> list[str]:
    """Uncaught JavaScript errors on the page, collected as the scenario runs."""
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    return errors


@pytest.fixture(autouse=True)
def _browser_ready(live_server: LiveServer, page: Page, js_errors: list[str]) -> None:
    """Start the server and browser before a scenario's first step.

    pytest-bdd resolves a step's fixtures only when the step runs, and a server first created mid-scenario ends up
    rejecting requests with a 400, as its host is missing from ALLOWED_HOSTS. The report also needs the page to exist
    after every step, including the ones that don't use it.

    This has to be a plain fixture dependency: starting the server with `request.getfixturevalue` hits the same 400.
    """


# Screenshots for the Cucumber report. They are taken only when a report is requested with `--cucumber-json`, and
# saved next to that file. `python -m e2e.report` then merges them into the report.
SCREENSHOTS: list[dict[str, Any]] = []
_LAST_DIGEST: dict[str, str] = {}  # Per scenario, to skip a screenshot that matches the one before it.


def _report_dir(config: pytest.Config) -> Path | None:
    json_path = config.getoption("cucumber_json_path", default=None)
    return Path(json_path).parent if json_path else None


def _screenshot(
    request: pytest.FixtureRequest, feature: Feature, scenario: Scenario, step: Step, *, failed: bool
) -> None:
    report_dir = _report_dir(request.config)
    if report_dir is None:
        return

    page: Page = request.getfixturevalue("page")
    if page.url == "about:blank":
        return  # Nothing has been opened yet, so there is nothing to show.

    file = Path("screenshots") / f"{len(SCREENSHOTS):03d}.jpg"
    (report_dir / file).parent.mkdir(parents=True, exist_ok=True)
    with suppress(PlaywrightError):  # A screenshot that can't be taken shouldn't hide the real result.
        # JPEG keeps the report small, as there are a lot of screenshots.
        image = page.screenshot(full_page=True, type="jpeg", quality=60, animations="disabled", caret="hide")
        digest = hashlib.sha256(image).hexdigest()
        if not failed and _LAST_DIGEST.get(scenario.name) == digest:
            return  # The page looks the same as after the previous step, so there is nothing new to show.
        _LAST_DIGEST[scenario.name] = digest
        (report_dir / file).write_bytes(image)
        SCREENSHOTS.append(
            {
                "feature": feature.rel_filename,
                "scenario": scenario.name,
                "line": step.line_number,
                "file": str(file),
                "failed": failed,
            }
        )


def pytest_sessionstart(session: pytest.Session) -> None:
    report_dir = _report_dir(session.config)
    if report_dir is not None:
        shutil.rmtree(report_dir / "screenshots", ignore_errors=True)


def pytest_sessionfinish(session: pytest.Session) -> None:
    report_dir = _report_dir(session.config)
    if report_dir is not None:
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "screenshots.json").write_text(json.dumps(SCREENSHOTS, indent=2))


def pytest_bdd_after_step(
    request: pytest.FixtureRequest,
    feature: Feature,
    scenario: Scenario,
    step: Step,
    step_func: Callable[..., Any],
    step_func_args: dict[str, Any],
) -> None:
    _screenshot(request, feature, scenario, step, failed=False)


def pytest_bdd_step_error(
    request: pytest.FixtureRequest,
    feature: Feature,
    scenario: Scenario,
    step: Step,
    step_func: Callable[..., Any],
    step_func_args: dict[str, Any],
    exception: Exception,
) -> None:
    _screenshot(request, feature, scenario, step, failed=True)


@pytest.fixture
def goto(page: Page, live_server: LiveServer) -> Callable[[str], None]:
    """Open a path on the live server, e.g. `goto("/pub/")`."""

    def _goto(path: str) -> None:
        page.goto(live_server.url + path)

    return _goto


@pytest.fixture
def sign_in(context: BrowserContext, live_server: LiveServer) -> Callable[..., User]:
    """Create a user linked to a person and sign the browser in as them.

    Logging in normally goes through Discord, so this creates the Django session directly and hands the browser
    its cookie.
    """

    def _sign_in(*, name: str = "Test Member", is_admin: bool = False, autopub: bool = False) -> User:
        person = PersonFactory.create(display_name=name, autopub=autopub)
        user = User.objects.create(username=name.lower().replace(" ", "-"), person=person, is_superuser=is_admin)

        client = Client()
        client.force_login(user)
        session = client.cookies[settings.SESSION_COOKIE_NAME]
        context.add_cookies([{"name": settings.SESSION_COOKIE_NAME, "value": session.value, "url": live_server.url}])
        return user

    return _sign_in
