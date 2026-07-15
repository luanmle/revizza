from django.contrib import admin
from django.urls import include, path

from .views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health_check),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/decks/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.catalog.moderator_urls")),
    path("api/v1/", include("apps.notes.urls")),
    path("api/v1/", include("apps.discussions.urls")),
    path("api/v1/", include("apps.protection.urls")),
    path("api/v1/", include("apps.sync.urls")),
    path("api/v1/", include("apps.suggestions.urls")),
    path("api/v1/", include("apps.notifications.urls")),
]
