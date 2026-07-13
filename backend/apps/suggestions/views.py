"""Endpoints de sugestão de mudança (contracts/suggestions.md, FR-013 a FR-017)."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Subscription
from apps.notes.models import Note

from .models import Suggestion, SuggestionTargetNote
from .serializers import BulkChangeSuggestionSerializer, ChangeSuggestionSerializer


def _subscriber_or_none(user, deck):
    return Subscription.objects.filter(user=user, deck=deck).first()


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
