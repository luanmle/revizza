from django.urls import path

from .views import ProtectionMeView

urlpatterns = [
    path("decks/<uuid:deck_id>/protection/me/", ProtectionMeView.as_view()),
]
