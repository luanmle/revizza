import importlib


def _prod_settings(monkeypatch):
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "api.example.com")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-only-secret-key-with-enough-entropy")
    monkeypatch.setenv("DJANGO_CORS_ALLOWED_ORIGINS", "https://app.example.com")
    import config.settings.prod as prod

    return importlib.reload(prod)


def test_production_forces_https_and_secure_cookies(monkeypatch):
    prod = _prod_settings(monkeypatch)

    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.SECURE_HSTS_SECONDS >= 31_536_000
    assert prod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True


def test_production_cors_origins_come_from_env(monkeypatch):
    prod = _prod_settings(monkeypatch)

    assert prod.CORS_ALLOWED_ORIGINS == ["https://app.example.com"]


def test_production_cache_is_shared_across_workers(monkeypatch):
    # T144: locks de sync e ratelimit exigem cache cross-process (não locmem)
    prod = _prod_settings(monkeypatch)

    assert (
        prod.CACHES["default"]["BACKEND"]
        == "django.core.cache.backends.db.DatabaseCache"
    )


def test_production_email_backend_is_env_driven(monkeypatch):
    monkeypatch.setenv(
        "DJANGO_EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"
    )
    monkeypatch.setenv("EMAIL_HOST", "smtp.example.com")
    prod = _prod_settings(monkeypatch)

    assert prod.EMAIL_BACKEND == "django.core.mail.backends.smtp.EmailBackend"
    assert prod.EMAIL_HOST == "smtp.example.com"


def test_security_rate_limits_are_enabled(settings):
    assert settings.RATELIMIT_ENABLE is True
    assert settings.RATELIMIT_SYNC_RATE == "1/10s"
    assert settings.RATELIMIT_SUGGESTION_RATE == "20/m"
    assert settings.RATELIMIT_PUBLISH_RATE
    assert settings.RATELIMIT_MEDIA_RATE
