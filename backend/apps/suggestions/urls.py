from django.urls import path

from . import views

urlpatterns = [
    path(
        "notes/<uuid:note_id>/suggestions/change/",
        views.ChangeSuggestionCreateView.as_view(),
    ),
    path("suggestions/bulk-change/", views.BulkChangeSuggestionCreateView.as_view()),
]
