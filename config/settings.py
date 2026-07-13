"""
Django settings for Community Health Inspector Analytics Dashboard.
Production-ready for Railway + Supabase PostgreSQL.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
load_dotenv(BASE_DIR.parent / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _normalize_database_url(url: str) -> str:
    """Railway/Heroku may provide postgres:// — Django expects postgresql://."""
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _railway_public_domain() -> str:
    return os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()


def _build_allowed_hosts() -> list[str]:
    hosts = _env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,.railway.app")
    railway_domain = _railway_public_domain()
    if railway_domain:
        hosts.append(railway_domain)
    if os.getenv("RAILWAY_ENVIRONMENT") or railway_domain:
        hosts.append(".up.railway.app")
    return list(dict.fromkeys(hosts))


def _normalize_csrf_origin(origin: str) -> str:
    """Django 4+ requires CSRF origins to include http:// or https://."""
    origin = origin.strip().rstrip("/")
    if not origin:
        return ""
    if "://" not in origin:
        return f"https://{origin}"
    return origin


def _build_csrf_trusted_origins() -> list[str]:
    origins = [_normalize_csrf_origin(o) for o in _env_list("CSRF_TRUSTED_ORIGINS")]
    origins = [o for o in origins if o]
    railway_domain = _railway_public_domain()
    if railway_domain:
        origins.extend([
            _normalize_csrf_origin(railway_domain),
            f"http://{railway_domain}",
        ])
    railway_static = os.getenv("RAILWAY_STATIC_URL", "").strip()
    if railway_static:
        origins.append(_normalize_csrf_origin(railway_static))
    return list(dict.fromkeys(origins))


HEALTH_DB_SCHEMA = os.getenv("HEALTH_DB_SCHEMA", "public")
HEALTH_DB_TABLE = os.getenv("HEALTH_DB_TABLE", "health_summary")


def _on_railway() -> bool:
    return bool(os.getenv("RAILWAY_ENVIRONMENT") or _railway_public_domain())


def _resolve_database_url() -> str:
    """Railway/Supabase may expose the URL under different variable names."""
    for name in ("DATABASE_URL", "DATABASE_PRIVATE_URL", "POSTGRES_URL"):
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _postgres_options() -> dict:
    return {
        "connect_timeout": 10,
        "options": f"-c search_path={HEALTH_DB_SCHEMA},public",
    }


def _build_database_from_env_vars() -> dict | None:
    """Use PGHOST / POSTGRES_* when a URL is not provided (e.g. Railway Postgres plugin)."""
    host = (
        os.getenv("PGHOST", "").strip()
        or os.getenv("POSTGRES_HOST", "").strip()
    )
    if not host or host in {"localhost", "127.0.0.1", "::1"}:
        return None

    options = _postgres_options()
    if _env_bool("DATABASE_SSL", True):
        options["sslmode"] = os.getenv("DATABASE_SSLMODE", "require")

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("PGDATABASE", os.getenv("POSTGRES_DB", "postgres")),
        "USER": os.getenv("PGUSER", os.getenv("POSTGRES_USER", "postgres")),
        "PASSWORD": os.getenv("PGPASSWORD", os.getenv("POSTGRES_PASSWORD", "")),
        "HOST": host,
        "PORT": os.getenv("PGPORT", os.getenv("POSTGRES_PORT", "5432")),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "600")),
        "OPTIONS": options,
    }


def _build_database_config() -> dict:
    database_url = _resolve_database_url()
    if database_url:
        database_url = _normalize_database_url(database_url)
        parsed = urlparse(database_url)
        query_params = dict(parse_qsl(parsed.query))

        options = _postgres_options()
        hostname = (parsed.hostname or "").lower()
        if "supabase" in hostname or _env_bool("DATABASE_SSL", True):
            options["sslmode"] = query_params.get("sslmode", "require")

        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": parsed.path.lstrip("/") or "postgres",
            "USER": parsed.username or "postgres",
            "PASSWORD": parsed.password or "",
            "HOST": parsed.hostname or "localhost",
            "PORT": str(parsed.port or 5432),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "600")),
            "OPTIONS": options,
        }

    from_env = _build_database_from_env_vars()
    if from_env:
        return from_env

    if _on_railway() or not _env_bool("DJANGO_DEBUG", True):
        raise ImproperlyConfigured(
            "DATABASE_URL is not set. In Railway → Variables, add your Supabase pooler URL "
            "(port 6543), for example: "
            "postgresql://postgres.PROJECT_REF:PASSWORD@aws-REGION.pooler.supabase.com:6543/postgres"
        )

    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "postgres"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "600")),
        "OPTIONS": _postgres_options(),
    }


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-change-in-production")
DEBUG = _env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = _build_allowed_hosts()

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "dashboard",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "dashboard" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dashboard.context_processors.user_access",
            ],
        },
    },
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Karachi")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "dashboard" / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "login"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "healthcare-dashboard",
        "TIMEOUT": int(os.getenv("DASHBOARD_CACHE_TTL", "300")),
    }
}

DASHBOARD_CACHE_TTL = int(os.getenv("DASHBOARD_CACHE_TTL", "300"))

DATABASES = {"default": _build_database_config()}
CSRF_TRUSTED_ORIGINS = _build_csrf_trusted_origins()

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO" if not DEBUG else "DEBUG")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "stream": sys.stdout,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", LOG_LEVEL),
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

IS_RAILWAY = _on_railway()

if not DEBUG:
    if SECRET_KEY in {"dev-only-change-in-production", "change-me-in-production", ""}:
        raise ImproperlyConfigured("Set a strong DJANGO_SECRET_KEY environment variable for production.")

    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", IS_RAILWAY)
    CSRF_COOKIE_SECURE = _env_bool("CSRF_COOKIE_SECURE", IS_RAILWAY)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0"))
    if SECURE_HSTS_SECONDS > 0:
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", False)

logging.getLogger(__name__).debug(
    "Settings loaded (DEBUG=%s, ALLOWED_HOSTS=%s, DB_HOST=%s)",
    DEBUG,
    ALLOWED_HOSTS,
    DATABASES["default"].get("HOST"),
)
