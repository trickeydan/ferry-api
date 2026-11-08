.PHONY: all clean fix lint type test test-cov e2e e2e-install hooks

CMD:=uv run
PYMODULE:=ferry
E2E:=e2e
E2E_REPORT:=$(E2E)/report
MANAGEPY:=$(CMD) ./manage.py
SETTINGS_MODULE:=ferry.core.settings.test

all: type test format lint
fix: lint-fix format

lint: 
	$(CMD) ruff check $(PYMODULE) $(E2E)

lint-fix: 
	$(CMD) ruff check --fix $(PYMODULE) $(E2E)

check:
	$(MANAGEPY) check

dev:
	$(MANAGEPY) runserver

format:
	find $(PYMODULE) -name "*.html" | xargs $(CMD) djhtml
	$(CMD) ruff format $(PYMODULE) $(E2E)

format-check:
	find $(PYMODULE) -name "*.html" | xargs $(CMD) djhtml --check
	$(CMD) ruff format --check $(PYMODULE) $(E2E)

hooks:
	uvx prek install

type: 
	$(CMD) mypy $(PYMODULE) $(E2E)

test: | $(PYMODULE)
	DJANGO_SETTINGS_MODULE=$(SETTINGS_MODULE) $(CMD) pytest -vv --cov=$(PYMODULE) $(PYMODULE)

# Browser tests. They are slower than the unit tests and need a browser, so `make test` leaves them out.
e2e-install:
	$(CMD) playwright install chromium

# Writes a Cucumber report with a screenshot of every step to e2e/report/index.html, even when a test fails.
e2e: | $(E2E)
	rm -rf $(E2E_REPORT)
	DJANGO_SETTINGS_MODULE=$(SETTINGS_MODULE) $(CMD) pytest -vv $(E2E) --screenshot only-on-failure --tracing retain-on-failure --output $(E2E)/test-results --cucumber-json=$(E2E_REPORT)/cucumber.json; \
		status=$$?; $(CMD) python -m $(E2E).report $(E2E_REPORT); exit $$status

test-cov:
	DJANGO_SETTINGS_MODULE=$(SETTINGS_MODULE) $(CMD) pytest -vv --cov=$(PYMODULE) $(PYMODULE) --cov-report html

clean:
	git clean -Xdf # Delete all files in .gitignore