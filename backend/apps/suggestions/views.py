"""Endpoints de sugestões e da tela Community Suggestions (contracts/suggestions.md)."""

from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Subscription
from apps.discussions.models import Comment
from apps.discussions.serializers import CommentSerializer
from apps.notes.models import Note
from config.pagination import DefaultCursorPagination

from .models import Suggestion, SuggestionTargetNote, SuggestionVote
from .serializers import (
    BulkChangeSuggestionSerializer,
    ChangeSuggestionSerializer,
    SuggestionDetailSerializer,
    SuggestionVoteSerializer,
)


def _subscriber_or_none(user, deck):
    return Subscription.objects.filter(user=user, deck=deck).first()


def _suggestion_for_subscriber(request, suggestion_id) -> Suggestion:
    """404 se não existe; 403 se o usuário não assina o deck da sugestão."""
    suggestion = get_object_or_404(
        Suggestion.objects.select_related("deck"), pk=suggestion_id
    )
    if not _subscriber_or_none(request.user, suggestion.deck):
        raise PermissionDenied("Assine o deck para acessar as sugestões.")
    return suggestion


def _create_change_suggestion(request, deck, notes, validated) -> Response:
    validated.pop("note_ids", None)
    with transaction.atomic():
        suggestion = Suggestion.objects.create(
            type=Suggestion.Type.CHANGE,
            deck=deck,
            author=request.user,
            **validated,
        )
        SuggestionTargetNote.objects.bulk_create(
            SuggestionTargetNote(suggestion=suggestion, note=note) for note in notes
        )
    return Response(
        ChangeSuggestionSerializer(suggestion).data, status=status.HTTP_201_CREATED
    )


class ChangeSuggestionCreateView(APIView):
    """POST /notes/{id}/suggestions/change/ — sugestão sobre uma única nota."""

    def post(self, request, note_id):
        note = get_object_or_404(Note, pk=note_id, deleted_at__isnull=True)
        if not _subscriber_or_none(request.user, note.deck):
            return Response(
                {"detail": "Assine o deck para sugerir mudanças."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ChangeSuggestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return _create_change_suggestion(
            request, note.deck, [note], serializer.validated_data
        )


class BulkChangeSuggestionCreateView(APIView):
    """POST /suggestions/bulk-change/ — uma única Suggestion cobrindo várias notas (FR-017)."""

    def post(self, request):
        serializer = BulkChangeSuggestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note_ids = serializer.validated_data["note_ids"]

        notes = list(
            Note.objects.filter(
                pk__in=note_ids, deleted_at__isnull=True
            ).select_related("deck")
        )
        if len(notes) != len(set(note_ids)):
            return Response(
                {"errors": {"note_ids": ["Uma ou mais notas não existem."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        decks = {note.deck for note in notes}
        if len(decks) != 1:
            return Response(
                {"errors": {"note_ids": ["Todas as notas devem ser do mesmo deck."]}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deck = decks.pop()
        if not _subscriber_or_none(request.user, deck):
            return Response(
                {"detail": "Assine o deck para sugerir mudanças."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return _create_change_suggestion(
            request, deck, notes, serializer.validated_data
        )


class DeckSuggestionListView(generics.ListAPIView):
    """GET /decks/{id}/suggestions/ — lista com filtros da tela (FR-021, FR-022)."""

    serializer_class = SuggestionDetailSerializer
    pagination_class = DefaultCursorPagination

    def get_queryset(self):
        from apps.catalog.models import Deck

        deck = get_object_or_404(Deck, pk=self.kwargs["deck_id"])
        if not _subscriber_or_none(self.request.user, deck):
            raise PermissionDenied("Assine o deck para acessar as sugestões.")

        qs = Suggestion.objects.filter(deck=deck).prefetch_related("target_notes")
        params = self.request.query_params
        for param, lookup in [
            ("type", "type"),
            ("status", "status"),
            ("author", "author_id"),
            ("note_id", "target_notes__note_id"),
            ("created_after", "created_at__gte"),
            ("created_before", "created_at__lte"),
        ]:
            if params.get(param):
                qs = qs.filter(**{lookup: params[param]})

        submission = params.get("submission")
        if submission == "individual":
            qs = qs.annotate(target_count=Count("target_notes")).filter(target_count=1)
        elif submission == "bulk":
            qs = qs.annotate(target_count=Count("target_notes")).filter(
                target_count__gt=1
            )
        return qs.distinct()


class SuggestionDetailView(generics.RetrieveAPIView):
    """GET /suggestions/{id}/ — detalhe com contagem de votos (FR-020)."""

    serializer_class = SuggestionDetailSerializer

    def get_object(self):
        return _suggestion_for_subscriber(self.request, self.kwargs["suggestion_id"])


class SuggestionVoteView(APIView):
    """POST /suggestions/{id}/votes/ — upsert do voto do usuário (FR-023)."""

    def post(self, request, suggestion_id):
        suggestion = _suggestion_for_subscriber(request, suggestion_id)
        serializer = SuggestionVoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        _, created = SuggestionVote.objects.update_or_create(
            suggestion=suggestion,
            user=request.user,
            defaults={"value": serializer.validated_data["value"]},
        )
        return Response(
            serializer.validated_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class SuggestionVoteMeView(APIView):
    """DELETE /suggestions/{id}/votes/me/ — remove o próprio voto (FR-023)."""

    def delete(self, request, suggestion_id):
        suggestion = _suggestion_for_subscriber(request, suggestion_id)
        SuggestionVote.objects.filter(suggestion=suggestion, user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SuggestionCommentPagination(DefaultCursorPagination):
    ordering = "created_at"  # thread em ordem cronológica


class SuggestionCommentsView(generics.ListCreateAPIView):
    """GET/POST /suggestions/{id}/comments/ — thread da sugestão (FR-024)."""

    serializer_class = CommentSerializer
    pagination_class = SuggestionCommentPagination

    def get_queryset(self):
        suggestion = _suggestion_for_subscriber(self.request, self.kwargs["suggestion_id"])
        return Comment.objects.filter(suggestion=suggestion)

    def perform_create(self, serializer):
        suggestion = _suggestion_for_subscriber(self.request, self.kwargs["suggestion_id"])
        serializer.save(author=self.request.user, suggestion=suggestion)
