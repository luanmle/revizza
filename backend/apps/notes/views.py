"""Busca e detalhe de notas (contracts/notes.md, FR-010, FR-011)."""

import uuid

from django.db.models import Q, TextField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.base import json_text_forms
from apps.catalog.models import Deck, Subscription
from config.pagination import DefaultCursorPagination

from .models import Note
from .serializers import NoteDetailSerializer, NoteListSerializer


def _require_subscription(user, deck):
    if not Subscription.objects.filter(user=user, deck=deck).exists():
        raise PermissionDenied("Assine o deck para acessar as notas.")


class DeckNoteListView(generics.ListAPIView):
    """GET /decks/{id}/notes/ — busca por termo (?q=) ou ID exato (?note_id=)."""

    serializer_class = NoteListSerializer
    pagination_class = DefaultCursorPagination

    def get_queryset(self):
        deck = get_object_or_404(Deck, pk=self.kwargs["deck_id"])
        _require_subscription(self.request.user, deck)

        qs = Note.objects.filter(deck=deck, deleted_at__isnull=True)

        note_id = self.request.query_params.get("note_id")
        if note_id:
            try:
                return qs.filter(pk=uuid.UUID(note_id))
            except ValueError:
                raise ValidationError({"note_id": ["Informe um UUID válido."]})

        term = self.request.query_params.get("q")
        if term:
            # ponytail: match textual no JSON dos campos, como no catálogo;
            # trocar por full-text/jsonb se decks de 10k notas ficarem lentos (FR-010)
            term_q = Q()  # formas escapada e literal (FR-056, pt-BR acentuado)
            for form in json_text_forms(term):
                term_q |= Q(fields_text__icontains=form)
            qs = qs.annotate(fields_text=Cast("field_values", TextField())).filter(
                term_q
            )
        return qs


class NoteDetailView(generics.RetrieveAPIView):
    """GET /notes/{id}/ — campos + note type (templates/css) para o preview (FR-011)."""

    serializer_class = NoteDetailSerializer

    def get_object(self):
        note = get_object_or_404(
            Note.objects.select_related("note_type", "deck"),
            pk=self.kwargs["note_id"],
            deleted_at__isnull=True,
        )
        _require_subscription(self.request.user, note.deck)
        return note
