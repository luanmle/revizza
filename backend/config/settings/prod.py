import os

from .base import *  # noqa: F403

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
