#!/bin/bash
set -e

export DJANGO_SETTINGS_MODULE=drf_api.settings
export PYTHONUNBUFFERED=1

# Migrations and static collection run once from the deploy job, never from
# each replica on start (they would race and re-collect on every boot).
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Applying migrations..."
  python manage.py migrate --noinput
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

# One-off containers (migrate, collectstatic, shell) pass their own command;
# only fall through to gunicorn when the image is started with no arguments.
if [ "$#" -gt 0 ]; then
  exec "$@"
fi

echo "Starting Gunicorn..."
exec gunicorn -c gunicorn_config.py drf_api.wsgi:application
