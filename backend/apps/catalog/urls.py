from django.urls import path

from . import views

urlpatterns = [
    path("", views.DeckListView.as_view()),
    path("<uuid:pk>/", views.DeckDetailView.as_view()),
    path("<uuid:deck_id>/subscriptions/", views.SubscriptionCreateView.as_view()),
    path("<uuid:deck_id>/subscriptions/me/", views.SubscriptionMeView.as_view()),
    path(
        "<uuid:deck_id>/moderators/",
        views.DeckModeratorListCreateView.as_view(),
    ),
    path(
        "<uuid:deck_id>/moderators/<uuid:user_id>/",
        views.DeckModeratorRemoveView.as_view(),
    ),
]
