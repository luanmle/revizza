"""Decisão de moderação: accept aplica na nota oficial e enfileira sync (FR-025 a FR-027)."""

import uuid

from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notes.models import Note

from .models import Suggestion, SuggestionTargetNote
from .permissions import is_active_deck_moderator
from .serializers import SuggestionDetailSerializer


class SuggestionDecisionView(APIView):
    """Base de accept/reject: só moderador ativo, decisão é terminal (409 se já decidida)."""

    def post(self, request, suggestion_id):
        suggestion = get_object_or_404(
            Suggestion.objects.select_related("deck"), pk=suggestion_id
        )
        if not is_active_deck_moderator(request.user, suggestion.deck):
            return Response(
                {"detail": "Apenas moderadores ativos do deck podem decidir sugestões."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if suggestion.status != Suggestion.Status.PENDING:
            # ponytail: checagem sem lock de linha — select_for_update se houver
            # decisão concorrente real em produção
            return Response(
                {"detail": "Sugestão já decidida — decisão é terminal (FR-027)."},
                status=status.HTTP_409_CONFLICT,
            )
        with transaction.atomic():
            self.decide(request, suggestion)
            suggestion.decided_by = request.user
            suggestion.save()
        return Response(SuggestionDetailSerializer(suggestion).data)


class SuggestionAcceptView(SuggestionDecisionView):
    """POST /suggestions/{id}/accept/ — aplica na nota oficial (FR-025, FR-026)."""

    def decide(self, request, suggestion):
        now = timezone.now()
        notes = [target.note for target in suggestion.target_notes.select_related("note")]
        if suggestion.type == Suggestion.Type.CHANGE:
            for note in notes:
                # campos propostos sobrescrevem; demais campos intactos
                note.field_values = {
                    **note.field_values,
                    **(suggestion.proposed_field_values or {}),
                }
                # avançar `mod` = entrar no delta de sync de todos os assinantes (FR-026)
                note.mod = now
                note.save()
        elif suggestion.type == Suggestion.Type.DELETION:
            for note in notes:
                note.deleted_at = now
                note.mod = now
                note.save()
        elif suggestion.type == Suggestion.Type.NEW_NOTE:
            note = Note.objects.create(
                deck=suggestion.deck,
                note_type=suggestion.deck.note_type,
                field_values=suggestion.proposed_field_values,
                tags=suggestion.proposed_tags,
                guid=uuid.uuid4().hex,
                mod=now,
            )
            SuggestionTargetNote.objects.create(suggestion=suggestion, note=note)
            suggestion.deck.__class__.objects.filter(pk=suggestion.deck_id).update(
                note_count=F("note_count") + 1
            )
        suggestion.status = Suggestion.Status.ACCEPTED


class SuggestionRejectView(SuggestionDecisionView):
    """POST /suggestions/{id}/reject/ — rejeita com motivo opcional (FR-025, FR-027)."""

    def decide(self, request, suggestion):
        suggestion.status = Suggestion.Status.REJECTED
        suggestion.rejection_reason = request.data.get("rejection_reason") or None
