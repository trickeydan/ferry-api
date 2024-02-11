#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

python /app/manage.py collectstatic --noinput
python /app/manage.py migrate

DJANGO_SETTINGS_MODULE=ferry.core.settings.prod /app/.venv/bin/gunicorn ferry.core.wsgi:application --bind 0.0.0.0:8000 --chdir=/app