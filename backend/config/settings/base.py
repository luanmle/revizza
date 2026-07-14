"""Settings comuns a todos os ambientes. Use config.settings.dev ou config.settings.prod."""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only")

DEBUG = False

ALLOWED_HOSTS: list[str] = []

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.accounts",
    "apps.catalog",
    "apps.notes",
    "apps.discussions",
    "apps.suggestions",
    "apps.protection",
    "apps.sync",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",  # antes de qualquer middleware que responda
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # logo após SecurityMiddleware (doc whitenoise)
    "config.middleware.ApiVersionCompatibilityMiddleware",
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

# Postgres via Supabase (Supavisor pooled DATABASE_URL); sqlite como fallback de dev/teste.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
# Servido pelo whitenoise (único consumidor de static é o Django admin — moderação US13).
# ponytail: storage padrão, sem manifest/cache-busting; trocar por
# whitenoise.storage.CompressedManifestStaticFilesStorage se admin static virar gargalo.
STATIC_ROOT = BASE_DIR / "staticfiles"
# Console por padrão (dev/teste); prod troca por SMTP via env (T145 / FR-050)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "AnkiHub Brasil <nao-responda@localhost>"
)

# --- CORS (T129): frontend e backend são deploys separados (plan) ---
CORS_ALLOWED_ORIGINS = [
    origin
    for origin in os.environ.get(
        "DJANGO_CORS_ALLOWED_ORIGINS", "http://localhost:3000"
    ).split(",")
    if origin
]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Supabase ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
PASSWORD_RESET_REDIRECT_URL = os.environ.get(
    "PASSWORD_RESET_REDIRECT_URL",
    "http://localhost:3000/password-reset/callback",
)

# --- DRF: paginação por cursor + versionamento via header Accept (contracts/api-conventions.md) ---
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["config.authentication.SupabaseAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.DefaultCursorPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.AcceptHeaderVersioning",
    "DEFAULT_VERSION": "1",
    "ALLOWED_VERSIONS": ["1"],
}

# A versão anterior é reescrita para o contrato atual pelo middleware. Remover o
# alias somente depois que a janela de transição dos add-ons instalados terminar.
API_VERSION_ALIASES = {"0": "1"}

# --- django-ratelimit: rates compartilhados, usados via @ratelimit(rate=settings.X) nas views ---
RATELIMIT_ENABLE = True
RATELIMIT_SYNC_WINDOW_SECONDS = 10
RATELIMIT_SYNC_RATE = (
    f"1/{RATELIMIT_SYNC_WINDOW_SECONDS}s"  # FR-032: uma execução por usuário
)
RATELIMIT_SUGGESTION_RATE = "20/m"  # FR-052
RATELIMIT_PUBLISH_RATE = "10/h"  # T133: publish é evento único por deck
# T133: generoso o bastante para o fan-out de mídia de um sync run legítimo
RATELIMIT_MEDIA_RATE = "120/m"

# --- Sentry (T013): só inicializa se houver DSN configurado ---
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(dsn=SENTRY_DSN, send_default_pii=False)
