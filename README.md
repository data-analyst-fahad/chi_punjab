# Healthcare Analytics Dashboard

Modern Django 5 dashboard for CHI clinical indicators. Queries **Supabase PostgreSQL** directly — no CSV/Excel files.

## Stack

- Django 5 + Django REST Framework
- Bootstrap 5 + Plotly.js + DataTables
- Supabase PostgreSQL (`warehouse.fact_daily_health_summary` or `public.health_summary`)
- Service layer architecture with caching

## Quick Start

```powershell
cd d:\CHIs\healthcare_analytics_dashboard
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your Supabase pooler DATABASE_URL

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign in.

## Configuration

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase pooler connection string (IPv4-friendly) |
| `HEALTH_DB_SCHEMA` | `warehouse` or `public` |
| `HEALTH_DB_TABLE` | `fact_daily_health_summary` or `health_summary` |
| `DASHBOARD_CACHE_TTL` | Cache seconds (default 300) |

## Architecture

```
dashboard/
  models.py              # Unmanaged model (read-only from Supabase)
  services/
    filter_service.py    # Date presets + district filters
    dashboard_service.py # Overview KPI cards
    analytics_service.py # Program dashboards (ANC, MI, CN, CI, PNC, FP, Geo)
    report_service.py    # Paginated reports + CSV/Excel/PDF export
  views.py               # Thin views — no SQL here
  templates/             # Bootstrap 5 UI
  static/                # CSS + JavaScript (AJAX refresh)
```

## API Endpoints

All require authentication. Support `preset`, `start_date`, `end_date`, `district` query params.

- `GET /api/dashboard/` — Overview KPIs
- `GET /api/anc/` — ANC charts
- `GET /api/immunization/` — Maternal immunization
- `GET /api/child-immunization/` — Child immunization
- `GET /api/nutrition/` — Child nutrition
- `GET /api/pnc/` — PNC
- `GET /api/family-planning/` — Family planning
- `GET /api/geographic/` — District rankings
- `GET /api/reports/` — Paginated report data
- `GET /api/export/csv|excel|pdf/` — Filtered exports

## Production (Railway)

See **[DEPLOY.md](DEPLOY.md)** for full Railway deployment instructions.

Quick summary:

```powershell
pip install -r requirements.txt
python manage.py check --deploy
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

Set `DJANGO_DEBUG=False` and a strong `DJANGO_SECRET_KEY` in Railway Variables.
