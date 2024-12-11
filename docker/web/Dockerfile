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

# New stage for building assets
FROM node:20-slim as asset-builder

WORKDIR /app
RUN mkdir -p /app/assets /app/ferry/static

COPY package.json package-lock.json vite.config.ts tsconfig.json ./
COPY assets /app/assets/

# Install dependencies for asset building
RUN npm install

WORKDIR /app/

# Build assets
RUN ls /app && npm run build

FROM python:${PYTHON_VERSION} as runtime

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

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
COPY --from=asset-builder /app/ferry/static/ /app/static/

COPY --chown=ferry:ferry ferry /app/ferry
COPY --chown=ferry:ferry manage.py /app/manage.py

USER ferry

ENTRYPOINT ["/entrypoint"]