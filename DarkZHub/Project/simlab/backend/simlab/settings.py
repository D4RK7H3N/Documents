"""Django settings for the SimLab backend.

Configuration is environment-driven so the same code runs:
* locally with zero infrastructure (SQLite + Celery tasks inline), and
* in docker-compose (PostgreSQL + Redis + a real Celery worker).

See ``.env.example`` at the repository root for the variable reference.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------- #
# Environment helpers
# --------------------------------------------------------------------- #
def _load_dotenv(path: Path) -> None:
    """Minimal .env loader: KEY=VALUE lines, '#' comments, no quoting.

    Existing environment variables always win over file values, so
    docker-compose and the shell can override a checked-in .env.
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def env_bool(name: str, default: bool) -> bool:
    """Read a boolean environment variable ('1/true/yes/on' vs anything else)."""
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str) -> list[str]:
    """Read a comma-separated environment variable."""
    return [item for item in os.getenv(name, default).split(",") if item]


_load_dotenv(BASE_DIR / ".env")

# --------------------------------------------------------------------- #
# Core Django settings
# --------------------------------------------------------------------- #
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "corsheaders",
    # Local apps
    "experiments",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # must run before CommonMiddleware
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "simlab.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "simlab.wsgi.application"

# --------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------- #
# PostgreSQL when POSTGRES_HOST is set (docker-compose); SQLite otherwise
# so local development needs no running services.
if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "simlab"),
            "USER": os.getenv("POSTGRES_USER", "simlab"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "simlab"),
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            # File-based (not in-memory) test database: the sweep
            # concurrency test runs real threads on separate connections,
            # which in-memory SQLite cannot serve (each connection gets
            # its own empty database).  The OPTIONS timeout raises the
            # SQLite busy timeout so concurrent writers queue briefly
            # instead of failing immediately.
            "TEST": {"NAME": BASE_DIR / "db.test.sqlite3"},
            "OPTIONS": {"timeout": 20},
        }
    }

# --------------------------------------------------------------------- #
# Validation / i18n / static
# --------------------------------------------------------------------- #
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------- #
# DRF
# --------------------------------------------------------------------- #
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
}

# CORS: allow the Vite dev server to call the API (Phase 3 frontend).
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")

# --------------------------------------------------------------------- #
# Celery
# --------------------------------------------------------------------- #
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

# Without an explicitly configured broker (plain local dev) run tasks
# inline inside the request so the API is fully functional with zero
# infrastructure.  docker-compose sets CELERY_BROKER_URL, which disables
# eager mode and hands execution to the real worker.
CELERY_TASK_ALWAYS_EAGER = env_bool(
    "CELERY_TASK_ALWAYS_EAGER", default="CELERY_BROKER_URL" not in os.environ
)

# Hard per-task limits (seconds) matching the engine contract; individual
# tasks also declare soft_time_limit/time_limit on the decorator.
CELERY_TASK_TIME_LIMIT = 120
CELERY_TASK_SOFT_TIME_LIMIT = 110

# Filesystem broker: setting CELERY_BROKER_URL=filesystem:// runs Celery
# with plain folders as the queue -- a real, separate worker process with
# no Redis required.  Useful on machines without Docker/Redis (tasks are
# executed by `celery -A simlab worker`, exactly as with Redis, only the
# transport differs).
if CELERY_BROKER_URL.startswith("filesystem://"):
    _fs_dir = os.getenv("CELERY_FS_BROKER_DIR", str(BASE_DIR / ".celery-fs"))
    os.makedirs(_fs_dir, exist_ok=True)
    _processed_dir = os.path.join(_fs_dir, "processed")
    os.makedirs(_processed_dir, exist_ok=True)
    CELERY_BROKER_TRANSPORT_OPTIONS = {
        "data_folder_in": _fs_dir,
        "data_folder_out": _fs_dir,
        "store_processed": True,
        "processed_folder": _processed_dir,
    }
    # The DB row is the source of truth for results; no result backend needed.
    CELERY_RESULT_BACKEND = None
