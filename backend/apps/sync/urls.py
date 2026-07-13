from django.urls import path

from . import views

urlpatterns = [
    path("decks/<uuid:deck_id>/publish/", views.PublishView.as_view()),
    path("decks/<uuid:deck_id>/sync/delta/", views.DeltaView.as_view()),
    path("decks/<uuid:deck_id>/sync/full/", views.FullView.as_view()),
    path("media/<str:content_hash>/", views.MediaDownloadView.as_view()),
]
