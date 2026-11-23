import os
import sys
from datetime import timedelta
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

if (BASE_DIR / ".env").exists():
    with open(BASE_DIR / ".env", encoding="utf-8") as env_file:
        for line in env_file:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "dev-insecure-key-change-me-0123456789abcdefghij0123456789abcdefghij"
)
DEBUG = os.environ.get("DEBUG", "1") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1, grades.darkzhub.asia").split(",") if h]

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "accounts",
    "academics",
    "grading",
    "audit",
    "integration",
    "common",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ]
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"

if os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "NAME": os.environ.get("POSTGRES_DB", "grade_monitoring"),
            "USER": os.environ.get("POSTGRES_USER", "grade_monitoring"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", ""),
            "CONN_MAX_AGE": 60,
            "OPTIONS": {"connect_timeout": 5},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

if "test" in sys.argv:
    PASSWORD_HASHERS = ["common.hashers.FastTestHasher"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("common.permissions.IsReadyUser",),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardPagination",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {"user": "120/min", "anon": "60/min", "login": "5/min"},
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "EXCEPTION_HANDLER": "common.exceptions.error_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "TOKEN_OBTAIN_SERIALIZER": "accounts.serializers.LoginSerializer",
}

CORS_ALLOWED_ORIGINS = [
    o for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if o
]

CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "https://grades.darkzhub.asia").split(",") if o
]

INTEGRATION_KEY = os.environ.get("INTEGRATION_KEY", "")

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Manila"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

UNFOLD = {
    "SITE_TITLE": "Grade Monitor",
    "SITE_HEADER": "Grade Monitoring Administration",
    "SITE_SUBHEADER": "Sagay National High School",
    "SITE_LOGO": "logo.svg",
    "SITE_FAVICONS": [{"rel": "icon", "type": "image/svg+xml", "href": "/static/logo.svg"}],
    "THEME": "light",
    "STYLES": ["admin/styles.css"],
    "COLORS": {
        "primary": {
            "50": "#eef2ff",
            "100": "#e0e7ff",
            "200": "#c7d2fe",
            "300": "#a5b4fc",
            "400": "#818cf8",
            "500": "#6366f1",
            "600": "#4f46e5",
            "700": "#4338ca",
            "800": "#3730a3",
            "900": "#312e81",
            "950": "#1e1b4b",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Academic Operations",
                "items": [
                    {"title": "Learners", "icon": "school", "link": "/admin/academics/studentprofile/"},
                    {"title": "Assessments", "icon": "quiz", "link": "/admin/grading/assessment/"},
                    {"title": "Scores", "icon": "grade", "link": "/admin/grading/score/"},
                    {"title": "Class Assignments", "icon": "co_present", "link": "/admin/academics/classassignment/"},
                ],
            },
            {
                "title": "Computed Records",
                "items": [
                    {"title": "Quarterly Grades", "icon": "calendar_view_month", "link": "/admin/grading/quartergrade/"},
                    {"title": "Semester Grades", "icon": "view_week", "link": "/admin/grading/semestergrade/"},
                    {"title": "General Averages", "icon": "workspace_premium", "link": "/admin/grading/generalaverage/"},
                ],
            },
            {
                "title": "Administration",
                "items": [
                    {"title": "User Accounts", "icon": "manage_accounts", "link": "/admin/accounts/user/"},
                    {"title": "Subjects", "icon": "menu_book", "link": "/admin/academics/subject/"},
                    {"title": "Sections", "icon": "meeting_room", "link": "/admin/academics/section/"},
                    {"title": "Grading Config", "icon": "tune", "link": "/admin/grading/gradingconfig/"},
                ],
            },
            {
                "title": "Records",
                "items": [
                    {"title": "Audit Log", "icon": "history", "link": "/admin/audit/auditlog/"},
                    {"title": "Submissions", "icon": "outgoing_mail", "link": "/admin/grading/gradesubmission/"},
                    {"title": "Quarter Locks", "icon": "lock", "link": "/admin/grading/quarterlock/"},
                ],
            },
        ],
    },
    "LOGIN": {
        "image": "logo.svg",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
