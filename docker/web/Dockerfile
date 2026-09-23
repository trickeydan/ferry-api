ARG PYTHON_VERSION=3.13-slim-trixie

FROM python:${PYTHON_VERSION} as builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache

RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential git

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN touch README.md

RUN --mount=type=cache,target=$UV_CACHE_DIR uv sync --locked --group prod --no-dev --no-install-project

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

COPY ./docker/web/entrypoint.sh /entrypoint
RUN chmod +x /entrypoint
RUN chown ferry /entrypoint

COPY ./docker/web/start.sh /start
RUN chmod +x /start
RUN chown ferry /start

RUN mkdir /app/static
RUN chown ferry:ferry /app/static
RUN mkdir /app/media
RUN chown ferry:ferry /app/media

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY --chown=ferry:ferry ferry /app/ferry
COPY --chown=ferry:ferry manage.py /app/manage.py

USER ferry

ENTRYPOINT ["/entrypoint"]