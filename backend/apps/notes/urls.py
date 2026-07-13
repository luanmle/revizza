from django.urls import path

from . import views

urlpatterns = [
    path("decks/<uuid:deck_id>/notes/", views.DeckNoteListView.as_view()),
    path("notes/<uuid:note_id>/", views.NoteDetailView.as_view()),
]
