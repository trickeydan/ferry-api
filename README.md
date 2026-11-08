# Ferry Service


## Testing

`make test` runs the unit tests. `make lint`, `make type` and `make format-check` cover both `ferry/` and `e2e/`.

### Browser tests

`e2e/` holds browser tests, written as [pytest-bdd](https://pytest-bdd.readthedocs.io/) scenarios and driven by
[Playwright](https://playwright.dev/python/) against a live Django server. They are kept out of `make test`, as they
are slower and need a browser.

```sh
make e2e-install   # once: downloads Chromium
make e2e
```

They need network access, as the pages load Bootstrap, htmx and the emoji picker's images from CDNs. On a failure,
a screenshot and a trace are saved to `e2e/test-results/` (open a trace with `uv run playwright show-trace`).

Every run also writes a Cucumber report to `e2e/report/index.html`: a single self-contained page with each
scenario's steps and a screenshot after every step (click one to enlarge it). Failed scenarios are open by default.
`e2e/report/cucumber.json` holds the same results as standard Cucumber JSON, with the screenshots as embeddings, so it
can be fed to other Cucumber tools. Screenshots are only taken when a run is given `--cucumber-json`, as `make e2e` does.

- `e2e/features/*.feature` are the scenarios, in Gherkin.
- `e2e/steps/` has the step definitions. `common.py` holds the steps any feature can use, such as signing in, clicking
  and checking text. The other modules hold steps for one area.
- `e2e/test_*.py` bind each feature file to pytest with `scenarios(...)`. A new feature needs a new `.feature` file and
  a `test_<name>.py` that points at it.
- Sign-in normally goes through Discord, so the `sign_in` fixture creates the Django session directly and gives the
  browser its cookie. Test data is created through the same factories and services as the unit tests.
