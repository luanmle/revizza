def test_django_is_configured(settings):
    assert "django.contrib.staticfiles" in settings.INSTALLED_APPS
