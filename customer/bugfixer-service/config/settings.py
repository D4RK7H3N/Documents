import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def env(key, default=None):
    return os.environ.get(key, default)


SECRET_KEY = env("SECRET_KEY", "dev-only-insecure-change-me")
DEBUG = env("DEBUG", "0") == "1"
ALLOWED_HOSTS = [h.strip() for h in env("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h.strip()]

DASHBOARD_ORIGIN = env("DASHBOARD_ORIGIN", "").rstrip("/")
WIDGET_URL = env("WIDGET_URL", "").rstrip("/")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in env("CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()]
if DASHBOARD_ORIGIN and DASHBOARD_ORIGIN not in CSRF_TRUSTED_ORIGINS:
    CSRF_TRUSTED_ORIGINS.append(DASHBOARD_ORIGIN)

TRUST_CLOUDFLARE_HEADERS = env("TRUST_CLOUDFLARE_HEADERS", "false").lower() == "true"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") if TRUST_CLOUDFLARE_HEADERS else None
USE_X_FORWARDED_HOST = TRUST_CLOUDFLARE_HEADERS

if TRUST_CLOUDFLARE_HEADERS:
    SESSION_COOKIE_SAMESITE = "None"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "None"
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "bugfixer",
]

USE_R2 = env("USE_R2", "false").lower() == "true"
if USE_R2:
    INSTALLED_APPS.append("storages")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "bugfixer.middleware.AllowedOriginCorsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

if env("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "bugfixer"),
            "USER": env("POSTGRES_USER", "bugfixer"),
            "PASSWORD": env("POSTGRES_PASSWORD", "bugfixer"),
            "HOST": env("POSTGRES_HOST"),
            "PORT": env("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

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
MEDIA_URL = "/media/"
MEDIA_ROOT = env("MEDIA_ROOT", str(BASE_DIR / "media"))
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "report_ip": env("THROTTLE_ANON_IP", "60/h"),
        "report_key": env("THROTTLE_PROJECT_KEY", "120/h"),
    },
}

# --- bugfixer service settings ---
WORKDIR = Path(env("WORKDIR", str(BASE_DIR / "work")))
MAX_UPLOAD_BYTES = int(env("MAX_UPLOAD_BYTES", "5242880"))
RESULT_LOG_MAX_CHARS = int(env("RESULT_LOG_MAX_CHARS", "12000"))

WORKER_JOB_TIMEOUT = int(env("WORKER_JOB_TIMEOUT", "900"))
MAX_DIFF_BYTES = int(env("MAX_DIFF_BYTES", str(10 * 1024 * 1024)))
MAX_JOBS_PER_PROJECT_PER_HOUR = int(env("MAX_JOBS_PER_PROJECT_PER_HOUR", "20"))

LLM_API_KEY = env("LLM_API_KEY", "")
LLM_BASE_URL = env("LLM_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = env("LLM_MODEL", "gpt-4o-mini")
TRIAGE_MODEL = env("TRIAGE_MODEL", LLM_MODEL)
VISION_MODEL = env("VISION_MODEL", "gpt-4o")
LLM_TIMEOUT = int(env("LLM_TIMEOUT", "30"))

OPENCODE_BIN = env("OPENCODE_BIN", "opencode")
OPENCODE_MODEL = env("OPENCODE_MODEL", "")
OPENCODE_EXTRA_ARGS = env("OPENCODE_EXTRA_ARGS", "")
OPENCODE_TIMEOUT = int(env("OPENCODE_TIMEOUT", "900"))
TEST_TIMEOUT = int(env("TEST_TIMEOUT", "900"))

WORKER_ENV_ALLOWLIST = [v for v in env("WORKER_ENV_ALLOWLIST", "PATH,HOME").split(",") if v]
GITHUB_TOKEN = env("GITHUB_TOKEN", "")

SMTP_HOST = env("SMTP_HOST", "")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_USER = env("SMTP_USER", "")
SMTP_PASSWORD = env("SMTP_PASSWORD", "")
SMTP_FROM = env("SMTP_FROM", "")
SMTP_USE_TLS = env("SMTP_USE_TLS", "1") == "1"
NOTIFY_EMAIL = env("NOTIFY_EMAIL", "")

# Cloudflare Turnstile
TURNSTILE_SECRET_KEY = env("TURNSTILE_SECRET_KEY", "")
TURNSTILE_SITEVERIFY_URL = env(
    "TURNSTILE_SITEVERIFY_URL",
    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
)

# Cloudflare Access (staff paths only)
CF_ACCESS_ENABLED = env("CF_ACCESS_ENABLED", "false").lower() == "true"
CF_ACCESS_TEAM = env("CF_ACCESS_TEAM", "")
CF_ACCESS_AUD = env("CF_ACCESS_AUD", "")
CF_ACCESS_CERTS_URL = env(
    "CF_ACCESS_CERTS_URL",
    f"https://{CF_ACCESS_TEAM}.cloudflareaccess.com/cdn-cgi/access/certs" if CF_ACCESS_TEAM else "",
)
CF_ACCESS_CLOCK_SKEW = int(env("CF_ACCESS_CLOCK_SKEW", "60"))

# Cloudflare R2 (private bucket, django-storages S3 backend)
R2_ACCOUNT_ID = env("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY_ID = env("R2_ACCESS_KEY_ID", "")
R2_SECRET_ACCESS_KEY = env("R2_SECRET_ACCESS_KEY", "")
R2_BUCKET = env("R2_BUCKET", "")
R2_ENDPOINT_URL = env(
    "R2_ENDPOINT_URL",
    f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com" if R2_ACCOUNT_ID else "",
)
R2_SIGNED_URL_TTL = int(env("R2_SIGNED_URL_TTL", "300"))

if USE_R2:
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                "bucket_name": R2_BUCKET,
                "endpoint_url": R2_ENDPOINT_URL,
                "access_key": R2_ACCESS_KEY_ID,
                "secret_key": R2_SECRET_ACCESS_KEY,
                "region_name": "auto",
                "querystring_auth": True,
                "querystring_expire": R2_SIGNED_URL_TTL,
                "use_ssl": True,
                "file_overwrite": False,
            },
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
