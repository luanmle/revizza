from django.urls import path

from .views import DeckModeratorInviteAcceptView

urlpatterns = [
    path(
        "deck-moderator-invites/<uuid:invite_id>/accept/",
        DeckModeratorInviteAcceptView.as_view(),
    ),
]
