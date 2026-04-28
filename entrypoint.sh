#!/bin/bash
set -e

export DJANGO_SETTINGS_MODULE=drf_api.settings
export PYTHONUNBUFFERED=1

echo "✅ Applying migrations..."
python manage.py migrate --noinput

echo "✅ Collecting static files..."
python manage.py collectstatic --noinput

echo "✅ Creating superuser if not exists..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(email='admin@gmail.com').exists():
    User.objects.create_superuser(
        email='admin@gmail.com',
        password='admin12345',
        first_name='Super',
        last_name='Admin'
    )
EOF

# --- Start Gunicorn ---
# --- Start Gunicorn ---
echo "🚀 Starting Gunicorn..."
exec gunicorn -c gunicorn_config.py drf_api.wsgi:application
