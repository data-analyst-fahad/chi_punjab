# Deploy Community Health Inspector Analytics Dashboard on Railway

This guide deploys the Django 5 dashboard to [Railway](https://railway.com) using **Gunicorn**, **WhiteNoise**, and your existing **Supabase PostgreSQL** database.

---

## Architecture on Railway

```
Browser → Railway HTTPS → Gunicorn → Django → Supabase PostgreSQL (read-only health data)
                              ↓
                         WhiteNoise (static CSS/JS)
                         Django DB tables (auth/users/sessions via same DATABASE_URL)
```

---

## Prerequisites

- [Railway account](https://railway.com)
- [GitHub](https://github.com) repo with this project (recommended)
- Supabase **pooler** connection string (port **6543**)
- Python **3.12** (set via `runtime.txt`)

---

## Step 1 — Push code to GitHub

From your project folder:

```bash
cd healthcare_analytics_dashboard
git init
git add .
git commit -m "Prepare Railway deployment"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```

> `.env` is in `.gitignore` — never commit secrets.

---

## Step 2 — Create Railway project

1. Go to [railway.com/new](https://railway.com/new)
2. Choose **Deploy from GitHub repo**
3. Select your repository
4. Set **Root Directory** to `healthcare_analytics_dashboard` if the repo root is `CHIs/`

---

## Step 3 — Configure Railway service

Railway auto-detects Python via Nixpacks. These files control the build:

| File | Purpose |
|------|---------|
| `runtime.txt` | Python 3.12.7 |
| `requirements.txt` | Python dependencies |
| `Procfile` | Web process command |
| `railway.json` | Build + start commands |
| `scripts/start.sh` | migrate → collectstatic → users → gunicorn |

**Start command** (set automatically from `railway.json` / `Procfile`):

```bash
bash scripts/start.sh
```

---

## Step 4 — Set environment variables

In Railway → your service → **Variables**, add:

| Variable | Value | Required |
|----------|-------|----------|
| `DATABASE_URL` | `postgresql://postgres.REF:PASSWORD@aws-1-ap-south-1.pooler.supabase.com:6543/postgres` | Yes |
| `DJANGO_SECRET_KEY` | Generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"` | Yes |
| `DJANGO_DEBUG` | `false` | Yes |
| `HEALTH_DB_SCHEMA` | `public` | Yes |
| `HEALTH_DB_TABLE` | `health_summary` | Yes |
| `SUPERADMIN_PASSWORD` | Strong password for superadmin | Yes |
| `DASHBOARD_VIEWER_PASSWORD` | Strong password for H&PD | Yes |
| `DJANGO_ALLOWED_HOSTS` | `.railway.app` (optional — auto-configured) | No |
| `CSRF_TRUSTED_ORIGINS` | Leave **empty** (auto from Railway). If set, use full URL: `https://your-app.up.railway.app` | No |
| `DATABASE_SSL` | `true` | No (default) |
| `DASHBOARD_CACHE_TTL` | `300` | No |
| `WEB_CONCURRENCY` | `2` | No |

### Do NOT add Railway Postgres if using Supabase

Use your **Supabase pooler URL** as `DATABASE_URL`. Do not attach Railway's PostgreSQL plugin unless you migrate data.

---

## Step 5 — Generate public domain

1. Railway → service → **Settings** → **Networking**
2. Click **Generate Domain**
3. Railway sets `RAILWAY_PUBLIC_DOMAIN` automatically
4. `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` are auto-configured in `settings.py`

---

## Step 6 — Deploy

Railway deploys on every push to your connected branch.

Watch **Deployments** → **Build Logs** and **Deploy Logs** for:

```
==> Running database migrations
==> Collecting static files
==> Ensuring dashboard users exist
==> Starting Gunicorn on port ...
```

Open your Railway URL: `https://YOUR-APP.up.railway.app`

---

## Step 7 — Login

Default usernames (passwords from Railway variables):

| Username | Access |
|----------|--------|
| `superadmin` | Full access — all tabs, Reports, Settings, `/admin/` |
| `H&PD` | Dashboard tabs only (Overview, ANC, MI, CN, CI, PNC, FP, Geographic) |

Change passwords immediately via Railway variables and redeploy.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Application failed to respond** | Check Deploy Logs; ensure Gunicorn binds to `$PORT` |
| **DisallowedHost** | Verify `RAILWAY_PUBLIC_DOMAIN` is set; add domain to `DJANGO_ALLOWED_HOSTS` |
| **CSRF verification failed** | Leave `CSRF_TRUSTED_ORIGINS` empty, or use `https://your-app.up.railway.app` (must include `https://`) |
| **Database connection refused (localhost:5432)** | `DATABASE_URL` is missing in Railway Variables. Add your Supabase pooler URL (port **6543**) |
| **Database connection error** | Use Supabase **pooler** URL (port 6543), not direct `db.*.supabase.co` |
| **ImproperlyConfigured SECRET_KEY** | Set `DJANGO_SECRET_KEY` in Railway variables |
| **Static files 404** | Check build logs for `collectstatic`; WhiteNoise serves from `staticfiles/` |
| **Empty charts** | Confirm `HEALTH_DB_SCHEMA=public` and `HEALTH_DB_TABLE=health_summary` |
| **Build fails on Python version** | Ensure `runtime.txt` contains `python-3.12.7` |

### View logs

Railway → Deployments → select deployment → **View Logs**

---

## Updating the app

```bash
git add .
git commit -m "Update dashboard"
git push
```

Railway redeploys automatically.

---

## Local production test (before Railway)

```bash
cd healthcare_analytics_dashboard
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # fill in values
set DJANGO_DEBUG=false
python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py setup_dashboard_users
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

---

## Security checklist

- [ ] `DJANGO_DEBUG=false` on Railway
- [ ] Strong `DJANGO_SECRET_KEY`
- [ ] Strong `SUPERADMIN_PASSWORD` and `DASHBOARD_VIEWER_PASSWORD`
- [ ] Supabase credentials only in Railway Variables (not in code)
- [ ] `.env` not committed to git
- [ ] Custom domain + HTTPS enabled in Railway

---

## Files added/modified for Railway

See project README or deployment commit for the full list of production files:

- `config/settings.py` — Railway-aware production settings
- `Procfile` / `railway.json` / `scripts/start.sh` — deploy commands
- `runtime.txt` — Python 3.12
- `requirements.txt` — Gunicorn + WhiteNoise
- `.env.example` — all required variables
- `.gitignore` — excludes secrets and staticfiles
