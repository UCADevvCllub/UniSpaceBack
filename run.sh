#!/bin/bash

# Navigate to the backend directory
cd backend

# Apply any database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Start the Telegram bot in the background
#echo "Starting Telegram Bot..."
#python manage.py bot &

# Start the Django web server in the foreground
# justrunmy.app will supply the $PORT environment variable
echo "Starting Django Web Server..."
gunicorn auth_system.wsgi:application --bind 0.0.0.0:${PORT:-8000}
