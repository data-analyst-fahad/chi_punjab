#!/usr/bin/env bash
# Deploy CHI Healthcare Analytics Dashboard on Ubuntu/Debian.
# Run from project root on the server after copying files to /var/www/chi-dashboard

set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/chi-dashboard}"
PYTHON="${PYTHON:-python3}"

echo "==> Deploying in ${APP_DIR}"
cd "${APP_DIR}"

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Copy .env.example to .env and configure it first."
  exit 1
fi

echo "==> Creating virtual environment"
${PYTHON} -m venv .venv
source .venv/bin/activate

echo "==> Installing dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Django migrate (auth/session tables)"
python manage.py migrate --noinput

echo "==> Collecting static files"
python manage.py collectstatic --noinput

echo "==> Creating dashboard users"
python manage.py setup_dashboard_users

echo "==> Restarting service (if systemd unit installed)"
if systemctl is-enabled chi-dashboard.service >/dev/null 2>&1; then
  sudo systemctl restart chi-dashboard
  sudo systemctl status chi-dashboard --no-pager
else
  echo "Systemd service not installed yet. Start manually:"
  echo "  gunicorn config.wsgi:application -c deploy/gunicorn.conf.py"
fi

echo "==> Deploy complete"
