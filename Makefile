.PHONY: all clean lint type test test-cov

CMD:=poetry run
PYMODULE:=ferry
MANAGEPY:=$(CMD) ./manage.py

all: type test format lint

lint: 
	 $(CMD) ruff check $(PYMODULE)

lint-fix: 
	$(CMD) ruff check --fix $(PYMODULE)

check:
	$(MANAGEPY) check

dev:
	$(MANAGEPY) runserver

format:
	$(CMD) find $(PYMODULE) -name "*.html" | xargs djhtml
	$(CMD) ruff format $(PYMODULE)

format-check:
	$(CMD) find $(PYMODULE) -name "*.html" | xargs djhtml --check
	$(CMD) ruff format --check $(PYMODULE)

type: 
	mypy $(PYMODULE)

test: | $(PYMODULE)
	DJANGO_SETTINGS_MODULE=ferry.core.settings pytest -vv --cov=. $(PYMODULE)

test-cov:
	DJANGO_SETTINGS_MODULE=ferry.core.settings pytest -vv --cov=. $(PYMODULE) --cov-report html

clean:
	git clean -Xdf # Delete all files in .gitignore