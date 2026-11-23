import os
import socket
import sys
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env (SECRET_KEY, DB_*, etc.)
from dotenv import load_dotenv  # noqa: E402

load_dotenv(BASE_DIR / ".env")


# ============================================================================
# AUTO-DETECT LOCAL IP ADDRESS
# ============================================================================
def get_local_ip():
    """Auto-detect local IP address for LAN deployment."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# SECURITY WARNING: keep the secret key used in production secret!
# Fail hard if SECRET_KEY is not set — never use a fallback default.
SECRET_KEY = os.environ["SECRET_KEY"]

# SECURITY WARNING: don't run with debug turned on in production!
ENVIRONMENT = os.getenv("ENVIRONMENT", "production").lower()
DEBUG = os.getenv("DEBUG", "False").lower() in ["true", "1", "yes"]

# Hard guard: DEBUG=True renders Django's technical error pages, which expose
# settings, source code and local variables. Never allow it in production.
if ENVIRONMENT in ("production", "prod") and DEBUG:
    raise ImproperlyConfigured(
        "DEBUG must be False when ENVIRONMENT=production. "
        "Unset DEBUG in .env or set DEBUG=False."
    )

# ============================================================================
# ALLOWED HOSTS FOR LAN DEPLOYMENT
# ============================================================================
# Auto-detect IP or use environment variable
DETECTED_IP = os.getenv("SERVER_IP") or get_local_ip()
SERVER_IP = DETECTED_IP

DEFAULT_ALLOWED_HOSTS = ",".join(
    [
        SERVER_IP,
        "sms.darkzhub.asia",
        # The proxy Worker forwards with Host: sms2-api.darkzhub.asia.
        "sms2-api.darkzhub.asia",
        "dashboard.darkzhub.asia",
        # Backward compatibility: installed desktop clients still call the
        # gateway host directly until they are reissued (P4). Server-side only.
        "gw.darkzhub.asia",
        "www.darkzhub.asia",
        "localhost",
        "127.0.0.1",
    ]
)

# Env-driven so deployments don't require editing this file.
ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("ALLOWED_HOSTS", DEFAULT_ALLOWED_HOSTS).split(",")
    if h.strip()
]

# Never accept a wildcard host outside DEBUG.
if not DEBUG and (ALLOWED_HOSTS == ["*"] or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured(
        "ALLOWED_HOSTS must not contain '*' when DEBUG is False."
    )

# 'testserver' is Django's in-process test client hostname. Strip it from
# production (it is never a legitimate public host) but keep it while the test
# runner is active, otherwise every APIClient test 400s with DisallowedHost.
_RUNNING_TESTS = len(sys.argv) > 1 and sys.argv[1] in {"test", "pytest"}
if not DEBUG and not _RUNNING_TESTS and "testserver" in ALLOWED_HOSTS:
    ALLOWED_HOSTS.remove("testserver")

# ============================================================================
# JAZZMIN ADMIN THEME
# ============================================================================
JAZZMIN_SETTINGS = {
    "site_title": "School Admin",
    "site_header": "School Management System",
    "site_brand": "SMS",
    "welcome_sign": "Welcome to School Management System",
    "copyright": "School Management System",
    "site_logo": None,
    "login_logo": None,
    "site_logo_classes": "img-circle",
    "custom_css": "css/admin_custom.css",
    "topmenu_links": [
        {"name": "Home", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "View Site", "url": "/", "new_window": True},
    ],
    "show_sidebar": True,
    "navigation_expanded": True,
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "students": "fas fa-user-graduate",
        "staff": "fas fa-chalkboard-teacher",
        "products": "fas fa-box",
        "sales": "fas fa-cash-register",
        "payments": "fas fa-credit-card",
        "cashier": "fas fa-money-bill-wave",
        "revenue": "fas fa-chart-line",
        "tuition": "fas fa-file-invoice-dollar",
        "tours": "fas fa-bus",
        "dorm": "fas fa-bed",
        "assessment": "fas fa-clipboard-check",
        "tracks": "fas fa-road",
        "graduation": "fas fa-graduation-cap",
        "school_config": "fas fa-cogs",
    },
    "default_icon_parents": "fas fa-folder",
    "default_icon_children": "fas fa-circle",
    "related_modal_active": True,
    "use_google_fonts_cdn": True,
    "changeform_format": "horizontal_tabs",
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark navbar-primary",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "darkly",
    "dark_mode_theme": "darkly",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}

# Application definition
INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "api",
    "students",
    "staff",
    "products",
    "sales",
    "payments",
    "cashier",
    "revenue",
    "tuition",
    "tours",
    "dorm",
    "assessment",
    "tracks",
    "graduation",
    "school_config",
    "dropouts",
    "accounts",
]

MIDDLEWARE = [
    # Mission P5: first in the list -> response phase runs last, so fingerprint
    # headers added by other middleware are stripped before the edge.
    "school_pos.middleware.ResponseHeaderSanitizerMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "school_pos.middleware.StaffAuthenticationMiddleware",
    "school_pos.middleware.DeviceTerminalMiddleware",
]

ROOT_URLCONF = "school_pos.urls"

# Template Configuration
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "staff" / "templates",
            BASE_DIR / "students" / "templates",
            BASE_DIR / "dorm" / "templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "school_config.context_processors.school_config",
            ],
        },
    },
]

WSGI_APPLICATION = "school_pos.wsgi.application"

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASES = {
    "default": {
        # Mission P6: retry only connection establishment (never queries) and
        # fail fast, so transient Windows/PG connection drops cannot hang all
        # Waitress worker threads and turn into 502s.
        "ENGINE": "school_pos.db_backends.postgresql",
        "NAME": os.getenv("DB_NAME", "SMSS"),
        "USER": os.getenv("DB_USER", "postgres"),
        "PASSWORD": os.environ["DB_PASSWORD"],
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        # Reuse connections. Without this every request opens a new Postgres
        # connection, which exhausts max_connections under modest load.
        "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        # Encrypt the DB link when the host is not loopback. Built
        # conditionally: passing sslmode="" is invalid for psycopg2.
        "OPTIONS": {
            **(
                {"sslmode": os.getenv("DB_SSLMODE", "require")}
                if os.getenv("DB_HOST", "localhost") not in ("localhost", "127.0.0.1", "")
                else {}
            ),
            "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "3")),
        },
        # Wrap each request in a transaction so a failed multi-write operation
        # (e.g. recording a payment + updating the balance) cannot half-apply.
        "ATOMIC_REQUESTS": True,
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    "school_pos.authentication.CaseInsensitiveAuthBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# Login URL for Django admin (use admin's built-in login page)
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# Whitenoise serves static files; collectstatic runs at build time on Vercel.
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (user uploads)
# WARNING: Vercel's filesystem is read-only at runtime — uploads saved to
# MEDIA_ROOT will NOT persist across function invocations. For production on
# Vercel, use S3 / R2 / Cloudinary instead. See:
#   https://vercel.com/docs/storage
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Release feed for the Electron app's auto-updater. The installers are stored
# on this machine and served from /releases/ ; GitHub Releases is only a
# mirror for the clients that were built before this switch.
RELEASES_ROOT = BASE_DIR / "releases"

# Canonical public origin used to build absolute media/logo URLs.
# Never derive these from the incoming request: behind the Cloudflare tunnel the
# request looks like plain HTTP (producing http:// asset URLs that browsers
# block as mixed content) and the Host header is attacker-controllable.
# Mission P3: the public origin is https://sms.darkzhub.asia - the backend
# hosts (sms2-api.darkzhub.asia, gw.darkzhub.asia) must not appear here.
PUBLIC_ORIGIN = os.getenv("PUBLIC_ORIGIN", "https://sms.darkzhub.asia").rstrip("/")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================================
# REST FRAMEWORK CONFIGURATION
# ============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # The browsable API renders an interactive, unauthenticated map of every
    # route and field whenever a browser sends Accept: text/html. JSON only.
    "DEFAULT_RENDERER_CLASSES": (
        ["rest_framework.renderers.JSONRenderer"]
        if not DEBUG
        else [
            "rest_framework.renderers.JSONRenderer",
            "rest_framework.renderers.BrowsableAPIRenderer",
        ]
    ),
    # Without pagination a single request dumps the entire database.
    "DEFAULT_PAGINATION_CLASS": "school_pos.pagination.RelativePagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "school_pos.throttling.CloudflareAwareAnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/hour",
        "user": "1000/hour",
    },
}

# ============================================================================
# CORS SETTINGS
# ============================================================================
CORS_ALLOW_ALL_ORIGINS = False

CORS_ALLOW_CREDENTIALS = True

# The Electron shell sends per-terminal identity headers on every request.
# django-cors-headers' default list does not include them, so the browser's
# preflight fails even though the origin itself is allowlisted.
from corsheaders.defaults import default_headers  # noqa: E402

CORS_ALLOW_HEADERS = (
    *default_headers,
    "X-Device-Id",
    "X-Device-Previous-Id",
)

# Mission P3: the browser now talks same-origin to https://sms.darkzhub.asia -
# the legacy backend hosts (sms2-api, gw) and the alternate gateway are gone.
DEFAULT_CORS_ORIGINS = [
    "https://sms.darkzhub.asia",
    # Dev/Electron shell talks to the public origin through the tunnel, so its
    # http://localhost origin must be allowed (explicit, never a wildcard).
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://[::1]:5173",  # Electron dev shell binds IPv6 loopback
]

# Dev-only origins. These are injected ONLY when DEBUG is on, so a production
# deploy can never end up with a credentialed allowlist entry for localhost or a
# throwaway tunnel that a third party could register after it lapses.
if DEBUG:
    DEFAULT_CORS_ORIGINS += [
        "http://localhost:5173",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
    ]
    _ngrok = os.getenv("NGROK_URL", "").strip().rstrip("/")
    if _ngrok:
        DEFAULT_CORS_ORIGINS.append(_ngrok)

# Env-driven so deployments don't require editing this file.
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ALLOWED_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS)).split(",")
    if o.strip()
]

# Wildcard CORS with credentials is never acceptable.
if not DEBUG and "*" in CORS_ALLOWED_ORIGINS:
    raise ImproperlyConfigured(
        "CORS_ALLOWED_ORIGINS must not contain '*' when DEBUG is False."
    )

# ============================================================================
# SESSION & COOKIE SETTINGS FOR LAN
# ============================================================================
SESSION_COOKIE_AGE = 28800
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_DOMAIN = None  # Allow cross-IP sessions
SESSION_COOKIE_SAMESITE = "Lax"
# Production is always HTTPS at the Cloudflare edge, so the Secure flag is on
# unless explicitly disabled for a plain-HTTP LAN install.
SESSION_COOKIE_SECURE = (
    os.getenv("SESSION_COOKIE_SECURE", str(not DEBUG)).lower() in ["true", "1", "yes"]
)
SESSION_COOKIE_PATH = "/"

# ============================================================================
# CSRF SETTINGS FOR LAN
# ============================================================================
CSRF_COOKIE_DOMAIN = None
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = (
    os.getenv("CSRF_COOKIE_SECURE", str(not DEBUG)).lower() in ["true", "1", "yes"]
)
CSRF_COOKIE_PATH = "/"
CSRF_COOKIE_HTTPONLY = False  # JavaScript needs to access it

CSRF_TRUSTED_ORIGINS = [
    o for o in CORS_ALLOWED_ORIGINS if o.startswith("https://")
]
# The Django admin/staff portal is also served on the legacy tunneled hosts;
# without these, its POST /admin/login/ fails CSRF with a bare 403.
CSRF_TRUSTED_ORIGINS += [
    "https://gw.darkzhub.asia",
    "https://sms2-api.darkzhub.asia",
]

# ============================================================================
# SECURITY SETTINGS
# ============================================================================
# Enable SSL redirect only on HTTPS-deployed environments (e.g., Railway)
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "False").lower() in ["true", "1", "yes"]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# NOTE: SECURE_BROWSER_XSS_FILTER and SECURE_CONTENT_SECURITY_POLICY were both
# removed from Django (deprecated 3.0, deleted 4.0). They were silently ignored
# and gave a false sense of protection. The modern equivalents are below;
# CSP requires a middleware in Django 4+ and is set in middleware.py.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"  # Clickjacking protection; use @xframe_options_exempt per-view if needed

# HSTS: only meaningful once the hostname is permanently HTTPS.
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "0" if DEBUG else "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False").lower() in [
    "true",
    "1",
    "yes",
]
SECURE_HSTS_PRELOAD = False

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================
# Vercel serverless environment check — Vercel sets VERCEL=1 automatically.
# On Vercel the filesystem is read-only (except /tmp), so file-based logging
# would crash. Fall back to console-only logging on Vercel.
ON_VERCEL = os.getenv("VERCEL", "").lower() in ["1", "true"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {asctime} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# File handler: only in non-Vercel environments (writable filesystem)
if not ON_VERCEL:
    LOGGING["handlers"]["file"] = {
        "class": "logging.FileHandler",
        "filename": BASE_DIR / "logs" / "django.log",
        "formatter": "verbose",
    }
    LOGGING["root"]["handlers"].append("file")
    LOGGING["loggers"]["django"]["handlers"].append("file")

    # Create logs directory if it doesn't exist
    LOGS_DIR = BASE_DIR / "logs"
    LOGS_DIR.mkdir(exist_ok=True)
