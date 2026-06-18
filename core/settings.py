"""
Django settings for core project.
"""

from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-dev-only-change-in-production",
)

DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")

REGISTRATION_ENABLED = os.getenv("REGISTRATION_ENABLED", "True").lower() in (
    "true",
    "1",
    "yes",
)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost,http://127.0.0.1",
    ).split(",")
    if origin.strip()
]

LOGIN_URL = "/login/"
LOGOUT_REDIRECT_URL = "/"

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api")
CHAT_MAX_CONTEXT_MESSAGES = int(os.getenv("CHAT_MAX_CONTEXT_MESSAGES", "50"))
OLLAMA_MODELS_CACHE_SECONDS = int(os.getenv("OLLAMA_MODELS_CACHE_SECONDS", "60"))
CHAT_MAX_IMAGE_SIZE_BYTES = int(
    os.getenv("CHAT_MAX_IMAGE_SIZE_BYTES", str(10 * 1024 * 1024))
)
CHAT_STREAM_RATE = os.getenv("CHAT_STREAM_RATE", "30/m")

_metrics_ips = os.getenv("METRICS_ALLOWED_IPS", "127.0.0.1")
METRICS_ALLOWED_IPS = [ip.strip() for ip in _metrics_ips.split(",") if ip.strip()]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "ollama",
    "accounts",
    "django_prometheus",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "ollama.context_processors.ollama_status",
                "accounts.context_processors.registration_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "ollama-webhub",
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

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

DATA_UPLOAD_MAX_MEMORY_SIZE = CHAT_MAX_IMAGE_SIZE_BYTES
FILE_UPLOAD_MAX_MEMORY_SIZE = CHAT_MAX_IMAGE_SIZE_BYTES

if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "ollama": {"level": "DEBUG" if DEBUG else "INFO", "propagate": True},
    },
}
