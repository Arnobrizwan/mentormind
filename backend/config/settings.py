"""
MentorMind settings — everything configurable comes from the environment.
No hardcoded hosts, credentials, or instance identity.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    INSTANCE_NAME=(str, "api-local"),
    REDIS_URL=(str, ""),
    REPLICA_URL=(str, ""),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-insecure-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Which API instance is serving — surfaced via the X-Served-By header
# so the load balancer round-robin is visible to clients.
INSTANCE_NAME = env("INSTANCE_NAME")

# ML microservice base URL (probed by /api/v1/system/)
ML_SERVICE_URL = env("ML_SERVICE_URL", default="")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "drf_spectacular",
    "corsheaders",
    "django_filters",
    "django_prometheus",
    "channels",
    "storages",
    # mentormind
    "apps.accounts",
    "apps.core",
    "apps.settings_engine",
    "apps.flags",
    "apps.notifications",
    "apps.chat",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.ServedByMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
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
ASGI_APPLICATION = "config.asgi.application"

# --- Databases: primary for writes, optional read replica -----------------
DATABASES = {
    "default": env.db_url("DATABASE_URL", default=f"sqlite:///{BASE_DIR}/db.sqlite3"),
}
if env("REPLICA_URL"):
    DATABASES["replica"] = env.db_url_config(env("REPLICA_URL"))
    DATABASE_ROUTERS = ["config.db_router.ReadReplicaRouter"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

# --- Cache: Redis when available, in-memory fallback for bare-metal dev ---
if env("REDIS_URL"):
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": env("REDIS_URL"),
            "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        }
    }
else:
    CACHES = {
        "default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    }

# --- Channels: Redis layer in Compose/K8s, in-memory for dev/tests --------
if env("REDIS_URL"):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [env("REDIS_URL")]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}
    }

# --- Email: console in dev, real SMTP via env in production ---------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="MentorMind <no-reply@mentormind.dev>"
)

# --- Celery ----------------------------------------------------------------
CELERY_BROKER_URL = env("REDIS_URL", default="") or "memory://"
CELERY_RESULT_BACKEND = env("REDIS_URL", default="") or None
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=not bool(env("REDIS_URL")))

# --- DRF / Auth ------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "MentorMind API",
    "DESCRIPTION": "Scalable EdTech platform — dynamic, ML-powered, no hardcode.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_ALL_ORIGINS = DEBUG and not CORS_ALLOWED_ORIGINS

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Object storage (Cloudflare R2 or any S3-compatible service): flipping one
# env var moves all uploads off the local disk — no code changes.
if env("R2_ENDPOINT_URL", default=""):
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "endpoint_url": env("R2_ENDPOINT_URL"),
            "access_key": env("R2_ACCESS_KEY_ID", default=""),
            "secret_key": env("R2_SECRET_ACCESS_KEY", default=""),
            "bucket_name": env("R2_BUCKET", default="mentormind"),
            "custom_domain": env("R2_PUBLIC_DOMAIN", default=None),
            "file_overwrite": False,
            "default_acl": None,
            "signature_version": "s3v4",
        },
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
