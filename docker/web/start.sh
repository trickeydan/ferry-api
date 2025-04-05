#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

export DJANGO_SETTINGS_MODULE=ferry.core.settings.prod

cd /app

python /app/manage.py collectstatic --noinput
python /app/manage.py migrate

/app/.venv/bin/granian --interface asginl ferry.core.asgi:application --workers 2 --no-ws --host 0.0.0.0 --port 8000
