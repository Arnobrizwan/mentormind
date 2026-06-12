#!/usr/bin/env bash
# Render free-tier boot: fresh demo data on every start (SQLite is
# ephemeral there — that keeps the public demo clean by design).
set -e
python manage.py migrate --noinput
python manage.py seed_demo
python manage.py collectstatic --noinput
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2
