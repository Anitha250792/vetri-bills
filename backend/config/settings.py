"""Vetri Bills settings.

Database: PostgreSQL when POSTGRES_DB is set (see .env.example / docker-compose.yml),
otherwise SQLite so the project runs with zero setup.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me-before-deploying-0123456789")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h for h in os.getenv("DJANGO_ALLOWED_HOSTS", "*").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

if not DEBUG:
    if SECRET_KEY.startswith("dev-only"):
        raise RuntimeError("Set DJANGO_SECRET_KEY before running with DJANGO_DEBUG=0")
    # Hosting platforms terminate HTTPS and forward plain HTTP to us.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # local
    "accounts",
    "catalog",
    "orders",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

if os.getenv("DATABASE_URL"):  # hosting providers (Render, Railway...) give one URL
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600)}
elif os.getenv("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
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

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
ON_VERCEL = bool(os.getenv("VERCEL"))
# Vercel's disk is read-only except /tmp. Bills are rebuilt on demand, so temporary storage is fine.
MEDIA_ROOT = Path("/tmp/media") if ON_VERCEL else BASE_DIR / "media"
WHITENOISE_USE_FINDERS = True  # serve admin CSS straight from the packages, no collectstatic needed
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- REST framework -------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticatedOrReadOnly",),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 12,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Vetri Bills API",
    "DESCRIPTION": "Shared backend for the Vetri Bills mobile app and web service.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- CORS (web client on Expo web / Vercel) --------------------------------
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    o for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o
]

# --- Business rules (used from Day 3 onwards) -------------------------------
EXPIRY_WARNING_DAYS = int(os.getenv("EXPIRY_WARNING_DAYS", "7"))

# --- Alerts -------------------------------------------------------------------
PUSH_ENABLED = os.getenv("PUSH_ENABLED", "1") == "1"
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
# Daily check time for `manage.py run_scheduler` (server time zone = TIME_ZONE)
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", "8"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", "0"))

# --- Payments ---------------------------------------------------------------
# Dummy keys + MOCK_PAYMENTS=1 means no call to Razorpay is made. For real Razorpay
# test mode: put your rzp_test_ keys in .env and set MOCK_PAYMENTS=0.
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_dummy")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "dummy_secret")
MOCK_PAYMENTS = os.getenv("MOCK_PAYMENTS", "1") == "1"
