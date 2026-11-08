"""Tests for the report generator. They don't need a browser."""

import base64
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from e2e.report import attach_screenshots, effective_statuses, render_html, summarise_error

PNG = b"\x89PNG fake image bytes"


def make_features() -> list[dict[str, Any]]:
    def step(keyword: str, name: str, line: int, status: str = "passed", **result: Any) -> dict[str, Any]:
        return {
            "keyword": keyword,
            "name": name,
            "line": line,
            "result": {"status": status, "duration": 2_000_000_000, **result},
        }

    return [
        {
            "uri": "features/demo.feature",
            "name": "Demo feature",
            "description": "Something <b>described</b>",
            "elements": [
                {
                    "name": "Works",
                    "steps": [step("Given", "I am here", 3), step("Then", 'I see "<ok>"', 4)],
                },
                {
                    "name": "Breaks",
                    "steps": [
                        step("Given", "I am here", 8),
                        step("Then", "I see a thing", 9, "failed", error_message="Boom: <expected>"),
                        step("And", "I see another", 10, "skipped"),
                    ],
                },
            ],
        }
    ]


def test_screenshots_are_embedded_in_the_matching_step(tmp_path: Path) -> None:
    (tmp_path / "screenshots").mkdir()
    (tmp_path / "screenshots/000.png").write_bytes(PNG)
    features = make_features()
    screenshots = [
        {
            "feature": "features/demo.feature",
            "scenario": "Works",
            "line": 4,
            "file": "screenshots/000.png",
            "failed": False,
        }
    ]

    attach_screenshots(features, screenshots, tmp_path)

    works, breaks = features[0]["elements"]
    assert "embeddings" not in works["steps"][0]
    assert works["steps"][1]["embeddings"] == [
        {"mime_type": "image/png", "data": base64.b64encode(PNG).decode(), "failed": False}
    ]
    assert all("embeddings" not in step for step in breaks["steps"])


def test_same_line_in_another_scenario_is_not_confused(tmp_path: Path) -> None:
    (tmp_path / "shot.png").write_bytes(PNG)
    features = make_features()
    # Line 8 only exists in "Breaks".
    screenshots = [
        {"feature": "features/demo.feature", "scenario": "Works", "line": 8, "file": "shot.png", "failed": False}
    ]

    attach_screenshots(features, screenshots, tmp_path)

    assert all("embeddings" not in step for scenario in features[0]["elements"] for step in scenario["steps"])


def test_html_summarises_results_and_escapes_content() -> None:
    html = render_html(make_features(), generated_at=datetime(2026, 11, 8, 12, 30, tzinfo=UTC))

    assert "<strong>2</strong> scenarios" in html
    assert "<strong>1</strong> passed" in html
    assert "<strong>1</strong> failed" in html
    assert "2026-11-08 12:30 UTC" in html
    assert "Something &lt;b&gt;described&lt;/b&gt;" in html
    assert "I see &quot;&lt;ok&gt;&quot;" in html
    assert "Boom: &lt;expected&gt;" in html
    assert "<b>described</b>" not in html


def test_html_opens_only_failed_scenarios() -> None:
    html = render_html(make_features())

    assert html.count('<details class="scenario" open>') == 1
    assert html.count('<details class="scenario">') == 1


def test_html_shows_screenshots_inline() -> None:
    features = make_features()
    features[0]["elements"][1]["steps"][1]["embeddings"] = [{"mime_type": "image/png", "data": "QUJD", "failed": True}]

    html = render_html(features)

    assert 'src="data:image/png;base64,QUJD"' in html
    assert 'class="shot failed"' in html


PYTEST_ERROR = """fixturefunc = <function should_see at 0x1075fb5e0>
    def call_fixture_func(fixturefunc, request, kwargs):
>       fixture_result = fixturefunc(**kwargs)

page = <Page url='http://localhost:61350/'>

>       expect(page.get_by_text(text)).to_be_visible()
E       AssertionError: Locator expected to be visible
E       Actual value: None
E       Error: element(s) not found
E
E       Aria snapshot:
E       - navigation:
E         - link "Pub"

e2e/steps/common.py:55: AssertionError"""


def test_error_summary_keeps_the_assertion_and_location() -> None:
    assert summarise_error(PYTEST_ERROR) == (
        "AssertionError: Locator expected to be visible\n"
        "Actual value: None\n"
        "Error: element(s) not found\n"
        "e2e/steps/common.py:55: AssertionError"
    )


def test_error_summary_falls_back_to_the_whole_message() -> None:
    assert summarise_error("something odd happened") == "something odd happened"


def test_html_collapses_the_full_error() -> None:
    features = make_features()
    features[0]["elements"][1]["steps"][1]["result"]["error_message"] = PYTEST_ERROR

    html = render_html(features)

    assert "<summary>Full error</summary>" in html
    assert html.count("Aria snapshot") == 1  # Only in the collapsed full error.


def test_steps_after_a_failure_are_skipped() -> None:
    steps = make_features()[0]["elements"][1]["steps"]
    steps[2]["result"]["status"] = "failed"  # pytest-bdd marks the steps after a failure as failed, too.

    assert effective_statuses(steps) == ["passed", "failed", "skipped"]
