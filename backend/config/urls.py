from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/accounts/", include("apps.accounts.urls")),
    path("api/v1/decks/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.sync.urls")),
]
