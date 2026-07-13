#!/usr/bin/env bash
# Railway / production startup: migrate, static files, users, then Gunicorn.
set -euo pipefail

echo "==> Running database migrations"
python manage.py migrate --noinput

echo "==> Verifying database connection"
python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print('Database OK:', connection.settings_dict['HOST'], connection.settings_dict['PORT'], connection.settings_dict['USER'])"

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Ensuring dashboard users exist"
python manage.py setup_dashboard_users

echo "==> Starting Gunicorn on port ${PORT:-8000}"
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile - \
  --log-level "${GUNICORN_LOG_LEVEL:-info}"
