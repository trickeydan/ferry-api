"""Build the Cucumber report from a browser test run.

pytest-bdd writes the results as Cucumber JSON (`--cucumber-json`), and the test run saves a screenshot of each step
beside it. This merges the screenshots into the JSON as standard Cucumber embeddings, so other Cucumber tools can read
it too, and renders everything as one self-contained HTML page.

    uv run python -m e2e.report e2e/report
"""

import base64
import json
import re
import sys
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

STATUS_ICONS = {"passed": "✓", "failed": "✗", "skipped": "–"}

STYLE = """
:root {
  --bg: #f6f7f9; --surface: #ffffff; --fg: #1d232b; --muted: #65707d; --line: #d9dde3;
  --passed: #1a7f4b; --passed-bg: #e3f4ea; --failed: #b3261e; --failed-bg: #fbe4e2; --skipped: #65707d;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #12161b; --surface: #1b2128; --fg: #e6e9ed; --muted: #97a1ad; --line: #2e3844;
    --passed: #62d394; --passed-bg: #17382a; --failed: #ff8a80; --failed-bg: #3d1d1b; --skipped: #97a1ad;
  }
}
* { box-sizing: border-box; }
body { margin: 0; padding: 24px 16px 48px; background: var(--bg); color: var(--fg);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 960px; margin: 0 auto; display: grid; gap: 24px; }
h1, h2, h3, p { margin: 0; }
h1 { font-size: 24px; }
h2 { font-size: 18px; }
.muted { color: var(--muted); }
.summary { display: flex; flex-wrap: wrap; gap: 8px 24px; align-items: baseline; }
.summary strong { font-size: 20px; }
.badge { display: inline-block; padding: 1px 9px; border-radius: 10px; font-size: 12px; }
.badge.passed { color: var(--passed); background: var(--passed-bg); }
.badge.failed { color: var(--failed); background: var(--failed-bg); }
.feature { display: grid; gap: 8px; }
.feature > p { max-width: 70ch; }
details.scenario { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; }
details.scenario > summary { cursor: pointer; padding: 10px 14px; display: flex; gap: 10px; align-items: center; }
details.scenario[open] > summary { border-bottom: 1px solid var(--line); }
ol.steps { list-style: none; margin: 0; padding: 8px 14px 14px; display: grid; gap: 10px; }
.step { display: grid; gap: 6px; }
.step-line { display: flex; gap: 8px; align-items: baseline; }
.step .icon { width: 1.2em; text-align: center; font-weight: 600; }
.step.passed .icon { color: var(--passed); }
.step.failed .icon { color: var(--failed); }
.step.skipped, .step.skipped .icon { color: var(--skipped); }
.keyword { color: var(--muted); font-weight: 600; }
.duration { margin-left: auto; color: var(--muted); font-variant-numeric: tabular-nums; }
.error { margin: 0; padding: 8px 10px; background: var(--failed-bg); color: var(--failed); border-radius: 6px;
  white-space: pre-wrap; overflow-x: auto; font: 12px/1.4 ui-monospace, "SF Mono", Menlo, monospace; }
details.trace { margin-top: 4px; }
details.trace summary { cursor: pointer; color: var(--muted); font-size: 12px; }
.shot { margin-left: calc(1.2em + 8px); }
.shot img { display: block; max-width: 320px; width: 100%; border: 1px solid var(--line); border-radius: 6px;
  cursor: zoom-in; }
.shot.failed img { border-color: var(--failed); }
.shot.zoomed img { max-width: 100%; cursor: zoom-out; }
:focus-visible { outline: 2px solid var(--passed); outline-offset: 2px; }
"""

SCRIPT = """
document.querySelectorAll('.shot').forEach(function (shot) {
  shot.addEventListener('click', function () { shot.classList.toggle('zoomed'); });
});
"""


def attach_screenshots(features: list[dict[str, Any]], screenshots: list[dict[str, Any]], report_dir: Path) -> None:
    """Add each screenshot to its step as a Cucumber embedding."""
    by_step: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for screenshot in screenshots:
        key = (screenshot["feature"], screenshot["scenario"], screenshot["line"])
        by_step.setdefault(key, []).append(screenshot)

    for feature in features:
        for scenario in feature["elements"]:
            for step in scenario["steps"]:
                for screenshot in by_step.get((feature["uri"], scenario["name"], step["line"]), []):
                    data = base64.b64encode((report_dir / screenshot["file"]).read_bytes()).decode()
                    mime_type = "image/png" if screenshot["file"].endswith(".png") else "image/jpeg"
                    step.setdefault("embeddings", []).append(
                        {"mime_type": mime_type, "data": data, "failed": screenshot["failed"]}
                    )


def effective_statuses(steps: list[dict[str, Any]]) -> list[str]:
    """Each step's status, with the steps after the first failure shown as skipped as they never ran.

    pytest-bdd reports those steps as failed, without an error of their own.
    """
    statuses = []
    failed = False
    for step in steps:
        status = step["result"]["status"]
        statuses.append("skipped" if failed and status == "failed" else status)
        failed = failed or status == "failed"
    return statuses


def summarise_error(message: str) -> str:
    """The assertion and where it happened, without the pytest traceback and Playwright's page snapshot."""
    lines = message.splitlines()
    assertion = []
    for line in lines:
        if line.startswith("E "):
            if "Aria snapshot" in line:
                break
            assertion.append(line[1:].strip())
    location = next((line for line in reversed(lines) if re.match(r"\S+\.py:\d+: \w+", line)), "")
    summary = "\n".join(line for line in [*assertion, location] if line).strip()
    return summary or message


def _status_counts(features: list[dict[str, Any]]) -> tuple[int, int, float]:
    passed = failed = 0
    duration = 0.0
    for feature in features:
        for scenario in feature["elements"]:
            statuses = {step["result"]["status"] for step in scenario["steps"]}
            failed += "failed" in statuses
            passed += "failed" not in statuses
            duration += sum(step["result"].get("duration", 0) for step in scenario["steps"]) / 1e9
    return passed, failed, duration


def _render_step(step: dict[str, Any], status: str) -> str:
    seconds = step["result"].get("duration", 0) / 1e9
    parts = [
        f'<li class="step {escape(status)}">',
        '<div class="step-line">',
        f'<span class="icon" aria-label="{escape(status)}">{STATUS_ICONS.get(status, "?")}</span>',
        f'<span><span class="keyword">{escape(step["keyword"].strip())}</span> {escape(step["name"])}</span>',
        f'<span class="duration">{seconds:.2f}s</span>',
        "</div>",
    ]
    if error := step["result"].get("error_message"):
        parts.append(f'<pre class="error">{escape(summarise_error(error))}</pre>')
        parts.append(
            f'<details class="trace"><summary>Full error</summary><pre class="error">{escape(error)}</pre></details>'
        )
    for embedding in step.get("embeddings", []):
        failed = " failed" if embedding.get("failed") else ""
        alt = f"Screenshot {'of the failure ' if failed else ''}after: {step['name']}"
        parts.append(
            f'<div class="shot{failed}" role="button" tabindex="0" title="Click to enlarge">'
            f'<img alt="{escape(alt)}" src="data:{embedding["mime_type"]};base64,{embedding["data"]}"></div>'
        )
    parts.append("</li>")
    return "".join(parts)


def _render_scenario(scenario: dict[str, Any]) -> str:
    failed = any(step["result"]["status"] == "failed" for step in scenario["steps"])
    status = "failed" if failed else "passed"
    seconds = sum(step["result"].get("duration", 0) for step in scenario["steps"]) / 1e9
    steps = "".join(
        _render_step(step, step_status)
        for step, step_status in zip(scenario["steps"], effective_statuses(scenario["steps"]), strict=True)
    )
    return (
        f'<details class="scenario"{" open" if failed else ""}>'
        f'<summary><span class="badge {status}">{status}</span> <span>{escape(scenario["name"])}</span>'
        f'<span class="duration">{seconds:.2f}s</span></summary>'
        f'<ol class="steps">{steps}</ol></details>'
    )


def render_html(features: list[dict[str, Any]], *, generated_at: datetime | None = None) -> str:
    passed, failed, duration = _status_counts(features)
    generated_at = generated_at or datetime.now(tz=UTC)
    sections = []
    for feature in features:
        description = f"<p class='muted'>{escape(feature['description'])}</p>" if feature.get("description") else ""
        scenarios = "".join(_render_scenario(scenario) for scenario in feature["elements"])
        sections.append(
            f'<section class="feature"><h2>{escape(feature["name"])}</h2>{description}{scenarios}</section>'
        )

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ferry browser tests</title>
<style>{STYLE}</style>
</head>
<body>
<main>
<header class="summary">
<h1>Ferry browser tests</h1>
<span><strong>{passed + failed}</strong> scenarios</span>
<span class="badge passed"><strong>{passed}</strong> passed</span>
<span class="badge failed"><strong>{failed}</strong> failed</span>
<span class="muted">{duration:.1f}s &middot; {generated_at:%Y-%m-%d %H:%M} UTC</span>
</header>
{"".join(sections)}
</main>
<script>{SCRIPT}</script>
</body>
</html>
"""


def build(report_dir: Path) -> Path:
    cucumber_json = report_dir / "cucumber.json"
    screenshots_json = report_dir / "screenshots.json"

    features = json.loads(cucumber_json.read_text())
    screenshots = json.loads(screenshots_json.read_text()) if screenshots_json.exists() else []

    attach_screenshots(features, screenshots, report_dir)
    cucumber_json.write_text(json.dumps(features, indent=2))

    index = report_dir / "index.html"
    index.write_text(render_html(features))
    return index


if __name__ == "__main__":
    directory = Path(sys.argv[1] if len(sys.argv) > 1 else "e2e/report")
    print(f"Report written to {build(directory)}")  # noqa: T201
