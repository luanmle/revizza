from django.urls import path

from . import views

urlpatterns = [
    path("notes/<uuid:note_id>/comments/", views.NoteCommentsView.as_view()),
    path("comments/<uuid:comment_id>/", views.CommentDetailView.as_view()),
    path(
        "comments/<uuid:comment_id>/reports/",
        views.ReportCreateView.as_view(),
    ),
    path(
        "suggestion-comments/<uuid:comment_id>/reports/",
        views.SuggestionCommentReportCreateView.as_view(),
    ),
]
