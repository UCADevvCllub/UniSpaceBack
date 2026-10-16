#!/bin/bash

# Navigate to the backend directory
cd backend

# Apply any database migrations
echo "Ensuring linked_event_id column exists..."
python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'auth_system.settings')
django.setup()
from django.db import connection
if connection.vendor == 'postgresql':
    with connection.cursor() as cursor:
        cursor.execute('ALTER TABLE camphub_classevent ADD COLUMN IF NOT EXISTS linked_event_id bigint NULL CONSTRAINT camphub_classevent_linked_event_id_fk REFERENCES camphub_classevent(id) DEFERRABLE INITIALLY DEFERRED;')
        print('Successfully checked/created linked_event_id column in PostgreSQL!')
"

echo "Applying database migrations..."
python manage.py migrate --noinput

# logs_db is a separate database (see auth_system/db_router.py) that
# `migrate` doesn't touch unless told to explicitly -- without this,
# APILog/APISQLLog never get their tables created.
echo "Applying logs_db migrations..."
python manage.py migrate --database=logs_db --noinput

# Collect static files (admin, DRF, Jazzmin) so WhiteNoise can serve them
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the Telegram bot in the background
#echo "Starting Telegram Bot..."
#python manage.py bot &

# Start the Django web server in the foreground
# justrunmy.app will supply the $PORT environment variable
echo "Starting Django Web Server..."
gunicorn auth_system.wsgi:application --bind 0.0.0.0:${PORT:-8000}
