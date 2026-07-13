from django.urls import path

from . import decisions, views

urlpatterns = [
    path(
        "notes/<uuid:note_id>/suggestions/change/",
        views.ChangeSuggestionCreateView.as_view(),
    ),
    path(
        "notes/<uuid:note_id>/suggestions/deletion/",
        views.DeletionSuggestionCreateView.as_view(),
    ),
    path("suggestions/bulk-change/", views.BulkChangeSuggestionCreateView.as_view()),
    path(
        "decks/<uuid:deck_id>/suggestions/new-note/",
        views.NewNoteSuggestionCreateView.as_view(),
    ),
    path("decks/<uuid:deck_id>/suggestions/", views.DeckSuggestionListView.as_view()),
    path("suggestions/<uuid:suggestion_id>/", views.SuggestionDetailView.as_view()),
    path(
        "suggestions/<uuid:suggestion_id>/votes/",
        views.SuggestionVoteView.as_view(),
    ),
    path(
        "suggestions/<uuid:suggestion_id>/votes/me/",
        views.SuggestionVoteMeView.as_view(),
    ),
    path(
        "suggestions/<uuid:suggestion_id>/comments/",
        views.SuggestionCommentsView.as_view(),
    ),
    path(
        "suggestions/<uuid:suggestion_id>/accept/",
        decisions.SuggestionAcceptView.as_view(),
    ),
    path(
        "suggestions/<uuid:suggestion_id>/reject/",
        decisions.SuggestionRejectView.as_view(),
    ),
]
