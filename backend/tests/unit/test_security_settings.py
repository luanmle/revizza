import importlib


def test_production_forces_https_and_secure_cookies(monkeypatch):
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "api.example.com")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-only-secret-key-with-enough-entropy")

    prod = importlib.import_module("config.settings.prod")

    assert prod.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert prod.SECURE_SSL_REDIRECT is True
    assert prod.SESSION_COOKIE_SECURE is True
    assert prod.CSRF_COOKIE_SECURE is True
    assert prod.SECURE_HSTS_SECONDS >= 31_536_000
    assert prod.SECURE_HSTS_INCLUDE_SUBDOMAINS is True


def test_security_rate_limits_are_enabled(settings):
    assert settings.RATELIMIT_ENABLE is True
    assert settings.RATELIMIT_SYNC_RATE == "1/10s"
    assert settings.RATELIMIT_SUGGESTION_RATE == "20/m"
