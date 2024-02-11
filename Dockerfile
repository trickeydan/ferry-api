ARG PYTHON_VERSION=3.12-slim-bookworm

FROM python:${PYTHON_VERSION} as builder

WORKDIR /app

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

RUN pip install wheel poetry==1.7.1

RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential git

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN --mount=type=cache,target=$POETRY_CACHE_DIR poetry install --without dev --no-root

FROM python:${PYTHON_VERSION} as runtime

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install system packages required by Wagtail and wagtail.
RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential \
    libpq-dev \
 && rm -rf /var/lib/apt/lists/*

RUN addgroup --system ferry \
    && adduser --system --ingroup ferry ferry

COPY ./docker/entrypoint.sh /entrypoint
RUN chmod +x /entrypoint
RUN chown ferry /entrypoint

COPY ./docker/start.sh /start
RUN chmod +x /start
RUN chown ferry /start

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY --chown=ferry:ferry ferry /app/ferry
COPY --chown=ferry:ferry manage.py /app/manage.py

USER ferry

ENTRYPOINT ["/entrypoint"]