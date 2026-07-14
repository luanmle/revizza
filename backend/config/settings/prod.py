import os

from .base import *  # noqa: F403
from .base import DATABASES

DEBUG = False

ALLOWED_HOSTS = os.environ["DJANGO_ALLOWED_HOSTS"].split(",")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]

# Heroku termina TLS no router; forçar HTTPS atrás do proxy (FR: Secure by Default)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# T129: origens do frontend obrigatórias e explícitas em produção
CORS_ALLOWED_ORIGINS = os.environ["DJANGO_CORS_ALLOWED_ORIGINS"].split(",")

# Supavisor em transaction mode (porta 6543) não suporta cursores server-side;
# inofensivo em session mode, evita bug silencioso se a URL do pooler mudar.
DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True

# T144: lock de sync e django-ratelimit precisam de cache compartilhado entre
# workers do gunicorn. Tabela criada por `manage.py createcachetable` (Procfile).
# ponytail: cache em banco basta para locks de 10s; Redis se latência importar.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# T145: e-mail real via env (FR-050); qualquer provedor SMTP serve
EMAIL_BACKEND = os.environ.get(
    "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "true").lower() == "true"
