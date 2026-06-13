"""
MentorMind settings — everything configurable comes from the environment.
No hardcoded hosts, credentials, or instance identity.
"""

import sys
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# Test runs and offline management commands don't serve traffic, so the
# production secret/host guards below don't apply to them.
_RUNNING_TESTS = "test" in sys.argv or "pytest" in sys.modules

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["*"]),
    CORS_ALLOWED_ORIGINS=(list, []),
    INSTANCE_NAME=(str, "api-local"),
    REDIS_URL=(str, ""),
    REPLICA_URL=(str, ""),
)
environ.Env.read_env(BASE_DIR / ".env")

_INSECURE_KEY = "dev-only-insecure-key-change-me"
SECRET_KEY = env("SECRET_KEY", default=_INSECURE_KEY)
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# Fail fast: never boot a non-debug server process with the shipped fallback
# key or a wildcard host. Tests and offline commands are exempt.
if not DEBUG and not _RUNNING_TESTS:
    if SECRET_KEY == _INSECURE_KEY:
        raise RuntimeError("SECRET_KEY must be set to a unique value when DEBUG is off.")
    if ALLOWED_HOSTS == ["*"]:
        raise RuntimeError("ALLOWED_HOSTS must be set explicitly when DEBUG is off.")

# Which API instance is serving — surfaced via the X-Served-By header
# so the load balancer round-robin is visible to clients.
INSTANCE_NAME = env("INSTANCE_NAME")

# ML microservice base URL (probed by /api/v1/system/)
ML_SERVICE_URL = env("ML_SERVICE_URL", default="")
# Shared secret sent as X-API-Key on every ml-service call (empty = no auth)
ML_API_KEY = env("ML_API_KEY", default="")

# --- Web Push (PWA reminders) ---------------------------------------------
# Optional and OFF by default — set all three to enable push. Generate a
# VAPID keypair with: python manage.py generate_vapid_keys
VAPID_PUBLIC_KEY = env("VAPID_PUBLIC_KEY", default="")
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", default="")
VAPID_SUBJECT = env("VAPID_SUBJECT", default="mailto:admin@mentormind.dev")

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
    "rest_framework_simplejwt.token_blacklist",
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
    "apps.engagement",
    "apps.tutor",
    "apps.revision",
    "apps.planner",
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
# CONN_MAX_AGE keeps connections warm across requests (persistent pooling);
# health checks drop any that the DB closed under us.
_CONN_MAX_AGE = env.int("DB_CONN_MAX_AGE", default=600)
DATABASES = {
    "default": env.db_url("DATABASE_URL", default=f"sqlite:///{BASE_DIR}/db.sqlite3"),
}
DATABASES["default"]["CONN_MAX_AGE"] = _CONN_MAX_AGE
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
if env("REPLICA_URL"):
    DATABASES["replica"] = env.db_url_config(env("REPLICA_URL"))
    DATABASES["replica"]["CONN_MAX_AGE"] = _CONN_MAX_AGE
    DATABASES["replica"]["CONN_HEALTH_CHECKS"] = True
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
# Tests must run tasks inline even when a broker is available (CI provides
# Redis but no worker, so queued tasks would never execute).
CELERY_TASK_ALWAYS_EAGER = _RUNNING_TESTS or env.bool(
    "CELERY_TASK_ALWAYS_EAGER", default=not bool(env("REDIS_URL"))
)
# Periodic jobs (celery beat). The dropout-risk sweep flags disengaging
# students and opens remediation tickets for instructors every Monday.
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "weekly-dropout-risk-scan": {
        "task": "apps.engagement.tasks.scan_dropout_risk",
        "schedule": crontab(
            day_of_week=env("DROPOUT_SCAN_DAY", default="mon"),
            hour=env.int("DROPOUT_SCAN_HOUR", default=6),
            minute=0,
        ),
    },
    "weekly-digest": {
        "task": "apps.engagement.tasks.send_weekly_digest",
        "schedule": crontab(
            day_of_week=env("DIGEST_DAY", default="sun"),
            hour=env.int("DIGEST_HOUR", default=17),
            minute=0,
        ),
    },
    # Plans build before the risk scan so Monday's nudge reflects them.
    "weekly-study-plans": {
        "task": "apps.planner.tasks.build_weekly_plans",
        "schedule": crontab(
            day_of_week=env("PLANNER_DAY", default="mon"),
            hour=env.int("PLANNER_HOUR", default=5),
            minute=0,
        ),
    },
    # Daily web-push nudge: due flashcards + keep-your-streak. No-op unless
    # VAPID keys are configured, so it's safe to leave scheduled everywhere.
    "daily-revision-reminder": {
        "task": "apps.notifications.tasks.send_revision_reminders",
        "schedule": crontab(
            hour=env.int("REMINDER_HOUR", default=18),
            minute=0,
        ),
    },
}

# --- DRF / Auth ------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "PAGE_SIZE": env.int("API_PAGE_SIZE", default=20),
    # Per-IP / per-user rate limits — back-pressure against scraping and
    # brute force. Tune via env without a redeploy.
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        # Throttles off under the test runner so accumulated cache state can't
        # make assertions flaky; live in every real process.
        "anon": None if _RUNNING_TESTS else env("THROTTLE_ANON", default="60/min"),
        "user": None if _RUNNING_TESTS else env("THROTTLE_USER", default="240/min"),
        # Tight scope for credential endpoints — slows brute-force logins
        "auth": None if _RUNNING_TESTS else env("THROTTLE_AUTH", default="10/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=30)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    # Invalidate the old refresh token on rotation so a stolen one can't be
    # replayed after the legitimate user refreshes.
    "BLACKLIST_AFTER_ROTATION": True,
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
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": env.int("PASSWORD_MIN_LENGTH", default=10)},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Transport & cookie hardening -----------------------------------------
# Applied whenever DEBUG is off (any real deployment). All overridable by env
# so a TLS-terminating proxy or a non-HTTPS internal hop can opt out.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if not DEBUG and not _RUNNING_TESTS:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
