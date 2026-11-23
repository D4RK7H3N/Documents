import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-production-safeswapph')

# ── Environment ───────────────────────────────────────────────────────

DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get(
    'DJANGO_ALLOWED_HOSTS',
    'darkz.isroot.in,localhost,127.0.0.1'
).split(',')

INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'channels',
    'core',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'safeswap.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'safeswap.wsgi.application'
ASGI_APPLICATION = 'safeswap.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'safeswapph'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', 'darkzhen'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5433'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'core.CustomUser'

# ── Security (HTTPS / Cookies / Headers) ──────────────────────────────

SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'False') == 'True'
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'https://darkz.isroot.in'
).split(',')

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# ── REST Framework ────────────────────────────────────────────────────

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ),
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/hour',
        'user': '500/hour',
        'otp': '3/minute',
        'login': '5/minute',
        'register': '10/hour',
    },
    'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler',
    'COERCE_DECIMAL_TO_STRING': True,
}

# ── JWT ───────────────────────────────────────────────────────────────

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=6),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_OBTAIN_SERIALIZER': 'core.serializers.CustomTokenObtainPairSerializer',
}

# ── CORS ──────────────────────────────────────────────────────────────

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = os.environ.get(
    'CORS_ALLOWED_ORIGINS',
    'https://darkz.isroot.in'
).split(',')
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'authorization',
    'content-type',
    'origin',
    'x-requested-with',
]

# ── Logging ───────────────────────────────────────────────────────────

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'security_file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/security.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'security': {
            'handlers': ['console', 'security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ── Firebase Realtime DB ──────────────────────────────────────────────
FIREBASE_CREDENTIALS = {
    'type': os.environ.get('FIREBASE_TYPE', 'service_account'),
    'project_id': os.environ.get('FIREBASE_PROJECT_ID', 'safeswapph'),
    'private_key_id': os.environ.get('FIREBASE_PRIVATE_KEY_ID', ''),
    'private_key': os.environ.get('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
    'client_email': os.environ.get('FIREBASE_CLIENT_EMAIL', ''),
    'client_id': os.environ.get('FIREBASE_CLIENT_ID', ''),
    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
    'token_uri': 'https://oauth2.googleapis.com/token',
}

FIREBASE_DATABASE_URL = os.environ.get(
    'FIREBASE_DATABASE_URL',
    'https://safeswapph-default-rtdb.asia-southeast1.firebasedatabase.app',
)

# ── Semaphore PH (SMS / OTP) ──────────────────────────────────────────
SEMAPHORE_API_KEY = os.environ.get('SEMAPHORE_API_KEY', '')
SEMAPHORE_SENDER_NAME = os.environ.get('SEMAPHORE_SENDER_NAME', 'SafeSwapPH')

# ── GCash / Maya PayIn API ────────────────────────────────────────────
MAYA_API_KEY = os.environ.get('MAYA_API_KEY', '')
MAYA_API_SECRET = os.environ.get('MAYA_API_SECRET', '')
MAYA_BASE_URL = os.environ.get('MAYA_BASE_URL', 'https://sandbox.paymay.com.ph')

# ── DeepSeek API ──────────────────────────────────────────────────────
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API_URL = 'https://api.deepseek.com/v1/chat/completions'

# ── Cloudflare R2 ─────────────────────────────────────────────────────
R2_ENDPOINT_URL = os.environ.get('R2_ENDPOINT_URL', '')
R2_ACCESS_KEY_ID = os.environ.get('R2_ACCESS_KEY_ID', '')
R2_SECRET_ACCESS_KEY = os.environ.get('R2_SECRET_ACCESS_KEY', '')
R2_BUCKET_NAME = os.environ.get('R2_BUCKET_NAME', 'safeswapph')
R2_PUBLIC_URL = os.environ.get('R2_PUBLIC_URL', '')

# ── Jazzmin Admin Theme ──────────────────────────────────────────────

JAZZMIN_SETTINGS = {
    'site_title': 'SafeSwap PH Admin',
    'site_header': 'SafeSwap PH',
    'site_brand': '',
    'site_logo': 'core/images/safeswap_logo.svg',
    'login_logo': 'core/images/safeswap_logo.svg',
    'login_logo_dark': None,
    'site_logo_classes': 'img-circle',
    'site_icon': 'core/images/safeswap_icon.svg',
    'welcome_sign': 'Sign in to your admin account',
    'copyright': 'SafeSwap PH',
    'custom_css': 'core/css/admin_custom.css',
    'search_model': ['core.CustomUser', 'core.Trade', 'core.Listing'],
    'topmenu_links': [
        {'name': 'Home', 'url': 'admin:index'},
        {'name': 'View Site', 'url': '/api/'},
    ],
    'icons': {
        'core.CustomUser': 'fas fa-users',
        'core.Trade': 'fas fa-exchange-alt',
        'core.Listing': 'fas fa-list',
        'core.Escrow': 'fas fa-lock',
        'core.Commission': 'fas fa-money-bill',
        'core.Dispute': 'fas fa-gavel',
        'core.MiddleMan': 'fas fa-user-shield',
        'core.KYCVerification': 'fas fa-id-card',
        'core.Blacklist': 'fas fa-ban',
        'core.PlatformConfig': 'fas fa-cog',
        'core.PhoneOTP': 'fas fa-mobile-alt',
    },
    'default_icon_parents': 'fas fa-folder',
    'default_icon_children': 'fas fa-circle',
    'order_with_respect_to': [
        'core.Trade', 'core.Listing', 'core.CustomUser',
        'core.KYCVerification', 'core.Escrow', 'core.Commission',
        'core.Dispute', 'core.MiddleMan', 'core.Blacklist',
        'core.PlatformConfig', 'core.PhoneOTP',
    ],
    'index': 'admin/index.html',
    'show_sidebar': True,
    'navigation_expanded': True,
    'hide_apps': [],
    'hide_models': [],
    'related_modal_active': True,
    'use_google_fonts_cdn': True,
    'show_ui_builder': False,
    'changeform_format': 'horizontal_tabs',
    'language_chooser': False,
}

JAZZMIN_UI_TWEAKS = {
    'navbar_small_text': False,
    'footer_small_text': False,
    'body_small_text': False,
    'brand_small_text': False,
    'brand_colour': 'navbar-white',
    'accent': 'accent-purple',
    'navbar': 'navbar-white navbar-light',
    'no_navbar_border': False,
    'navbar_fixed': True,
    'layout_boxed': False,
    'footer_fixed': False,
    'sidebar_fixed': True,
    'sidebar': 'sidebar-light-purple',
    'sidebar_nav_small_text': False,
    'sidebar_disable_expand': False,
    'sidebar_nav_child_indent': True,
    'sidebar_nav_compact_style': False,
    'sidebar_nav_legacy_style': False,
    'sidebar_nav_flat_style': False,
    'theme': 'default',
    'dark_mode_theme': None,
    'button_classes': {
        'primary': 'btn-primary', 'secondary': 'btn-secondary',
        'info': 'btn-info', 'warning': 'btn-warning',
        'danger': 'btn-danger', 'success': 'btn-success',
    },
    'actions_sticky_top': True,
}

# ── Commission / Escrow defaults ──────────────────────────────────────
COMMISSION_TOTAL = 20
COMMISSION_CREATOR_CUT = 10
COMMISSION_MIDDLEMAN_CUT = 7
COMMISSION_RESERVE_CUT = 3
