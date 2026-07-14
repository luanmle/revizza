"""Threads de comentários gerais das notas (contracts/notes.md, FR-012)."""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notes.models import Note
from apps.notes.views import _require_subscription
from config.pagination import DefaultCursorPagination

from .models import Comment, Report
from .serializers import CommentSerializer, ReportSerializer


class NoteCommentPagination(DefaultCursorPagination):
    ordering = "created_at"


class NoteCommentsView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    pagination_class = NoteCommentPagination

    def get_note(self):
        note = get_object_or_404(
            Note.objects.select_related("deck"),
            pk=self.kwargs["note_id"],
            deleted_at__isnull=True,
        )
        _require_subscription(self.request.user, note.deck)
        return note

    def get_queryset(self):
        return Comment.objects.filter(note=self.get_note()).select_related("author")

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, note=self.get_note())


class CommentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Comment.objects.select_related("author")
    serializer_class = CommentSerializer
    lookup_url_kwarg = "comment_id"
    http_method_names = ["patch", "delete", "options"]

    def get_object(self):
        comment = super().get_object()
        if comment.author_id != self.request.user.id:
            raise PermissionDenied("Somente o autor pode alterar este comentário.")
        return comment

    def perform_update(self, serializer):
        serializer.save(edited_at=timezone.now())


class ReportCreateView(APIView):
    """Cria denúncia autenticada para comentário geral ou de sugestão (FR-048)."""

    thread_field = "note"

    def post(self, request, comment_id):
        comment = get_object_or_404(
            Comment, pk=comment_id, **{f"{self.thread_field}__isnull": False}
        )
        serializer = ReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = Report.objects.create(
            reporter=request.user,
            comment=comment,
            **serializer.validated_data,
        )
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)


class SuggestionCommentReportCreateView(ReportCreateView):
    thread_field = "suggestion"
