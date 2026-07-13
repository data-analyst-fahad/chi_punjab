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


def _build_database_config() -> dict:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "postgres"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "600")),
            "OPTIONS": {
                "connect_timeout": 10,
                "options": f"-c search_path={HEALTH_DB_SCHEMA},public",
            },
        }

    database_url = _normalize_database_url(database_url)
    parsed = urlparse(database_url)
    query_params = dict(parse_qsl(parsed.query))

    options: dict = {
        "connect_timeout": 10,
        "options": f"-c search_path={HEALTH_DB_SCHEMA},public",
    }

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

IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or _railway_public_domain())

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
