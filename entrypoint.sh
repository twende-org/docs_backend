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

echo "Starting Gunicorn..."
exec gunicorn -c gunicorn_config.py drf_api.wsgi:application
