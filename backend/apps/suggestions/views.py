"""Endpoints de sugestões e da tela Community Suggestions (contracts/suggestions.md)."""

import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django_ratelimit.decorators import ratelimit
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Deck, Subscription
from apps.discussions.models import Comment
from apps.discussions.serializers import CommentSerializer
from apps.notes.models import Note
from config.pagination import DefaultCursorPagination

from .models import Suggestion, SuggestionTargetNote, SuggestionVote
from .serializers import (
    BulkChangeSuggestionSerializer,
    ChangeSuggestionSerializer,
    DeletionSuggestionSerializer,
    NewNoteSuggestionSerializer,
    SuggestionDetailSerializer,
    SuggestionVoteSerializer,
)


def _suggestion_rate(_group, _request):
    return settings.RATELIMIT_SUGGESTION_RATE


def _rate_limit_response(request):
    if getattr(request, "limited", False):
        return Response(
            {"detail": "Limite de sugestões atingido. Tente novamente em um minuto."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": "60"},
        )
    return None


suggestion_ratelimit = method_decorator(
    ratelimit(
        group="suggestion-submission",
        key="user",
        rate=_suggestion_rate,
        method="POST",
        block=False,
    )
)


def _subscriber_or_none(user, deck):
    return Subscription.objects.filter(user=user, deck=deck).first()


def _target_context_prefetch():
    return Prefetch(
        "target_notes",
        queryset=SuggestionTargetNote.objects.select_related("note").annotate(
            open_suggestion_count=Count(
                "note__suggestion_targets",
                filter=Q(
                    note__suggestion_targets__suggestion__status=Suggestion.Status.PENDING
                ),
                distinct=True,
            )
        ),
    )


def _suggestion_for_subscriber(request, suggestion_id) -> Suggestion:
    """404 se não existe; 403 se o usuário não assina o deck da sugestão."""
    suggestion = get_object_or_404(
        Suggestion.objects.select_related("deck", "author").prefetch_related(
            _target_context_prefetch()
        ),
        pk=suggestion_id,
    )
    if not _subscriber_or_none(request.user, suggestion.deck):
        raise PermissionDenied("Assine o deck para acessar as sugestões.")
    return suggestion


def _change_validation_error(deck, notes, validated) -> Response | None:
    """Rejeita mudança vazia, com campo desconhecido ou no-op (FR-020, US4/AC4).

    Em lote, basta uma nota-alvo divergir da proposta para a correção compartilhada
    ser válida (FR-017).
    """
    fields = validated.get("proposed_field_values") or {}
    tags = validated.get("proposed_tags") or []
    if not fields and not tags:
        return Response(
            {"detail": "Proponha ao menos uma mudança de campo ou de tag."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    # notes garantidamente de um único tipo (T009/bulk e nota única); campos esperados
    # vêm do tipo das notas-alvo, não mais do deck (research.md Decisão 4)
    expected_fields = notes[0].note_type.field_names
    unknown = [f for f in fields if f not in expected_fields]
    if unknown:
        return Response(
            {
                "errors": {
                    "proposed_field_values": [
                        f"Campos desconhecidos: {', '.join(unknown)}."
                    ]
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    is_noop = all(
        all(note.field_values.get(f) == v for f, v in fields.items())
        and set(tags) <= set(note.tags)
        for note in notes
    )
    if is_noop:
        return Response(
            {"detail": "A sugestão não altera nada nas notas selecionadas."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None


def _create_change_suggestion(request, deck, notes, validated) -> Response:
    validated.pop("note_ids", None)
    if error := _change_validation_error(deck, notes, validated):
        return error
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

    @suggestion_ratelimit
    def post(self, request, note_id):
        if limited := _rate_limit_response(request):
            return limited
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

    @suggestion_ratelimit
    def post(self, request):
        if limited := _rate_limit_response(request):
            return limited
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
        if len({note.note_type_id for note in notes}) != 1:
            # invariante de data-model.md: uma mudança em lote cobre um só tipo de nota
            return Response(
                {
                    "errors": {
                        "note_ids": [
                            "Todas as notas devem ser do mesmo tipo de nota."
                        ]
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not _subscriber_or_none(request.user, deck):
            return Response(
                {"detail": "Assine o deck para sugerir mudanças."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return _create_change_suggestion(
            request, deck, notes, serializer.validated_data
        )


class NewNoteSuggestionCreateView(APIView):
    """POST /decks/{id}/suggestions/new-note/ — propõe nota completa (FR-018)."""

    @suggestion_ratelimit
    def post(self, request, deck_id):
        if limited := _rate_limit_response(request):
            return limited
        deck = get_object_or_404(Deck, pk=deck_id)
        if not _subscriber_or_none(request.user, deck):
            raise PermissionDenied("Assine o deck para sugerir uma nota nova.")
        serializer = NewNoteSuggestionSerializer(
            data=request.data, context={"deck": deck}
        )
        serializer.is_valid(raise_exception=True)
        suggestion = Suggestion.objects.create(
            type=Suggestion.Type.NEW_NOTE,
            deck=deck,
            author=request.user,
            **serializer.validated_data,
        )
        return Response(
            NewNoteSuggestionSerializer(suggestion, context={"deck": deck}).data,
            status=status.HTTP_201_CREATED,
        )


class DeletionSuggestionCreateView(APIView):
    """POST /notes/{id}/suggestions/deletion/ — propõe remoção (FR-019)."""

    @suggestion_ratelimit
    def post(self, request, note_id):
        if limited := _rate_limit_response(request):
            return limited
        note = get_object_or_404(
            Note.objects.select_related("deck"),
            pk=note_id,
            deleted_at__isnull=True,
        )
        if not _subscriber_or_none(request.user, note.deck):
            raise PermissionDenied("Assine o deck para sugerir a exclusão.")
        serializer = DeletionSuggestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            suggestion = Suggestion.objects.create(
                type=Suggestion.Type.DELETION,
                deck=note.deck,
                author=request.user,
                **serializer.validated_data,
            )
            SuggestionTargetNote.objects.create(suggestion=suggestion, note=note)
        return Response(
            DeletionSuggestionSerializer(suggestion).data,
            status=status.HTTP_201_CREATED,
        )


class DeckSuggestionListView(generics.ListAPIView):
    """GET /decks/{id}/suggestions/ — lista com filtros da tela (FR-021, FR-022)."""

    serializer_class = SuggestionDetailSerializer
    pagination_class = DefaultCursorPagination

    def get_queryset(self):
        deck = get_object_or_404(Deck, pk=self.kwargs["deck_id"])
        if not _subscriber_or_none(self.request.user, deck):
            raise PermissionDenied("Assine o deck para acessar as sugestões.")

        qs = (
            Suggestion.objects.filter(deck=deck)
            .select_related("author")
            .prefetch_related(_target_context_prefetch())
            # FR-054: contagens no annotate — sem query por sugestão na lista
            .annotate(
                likes=Count(
                    "votes",
                    filter=Q(votes__value=SuggestionVote.Value.LIKE),
                    distinct=True,
                ),
                dislikes=Count(
                    "votes",
                    filter=Q(votes__value=SuggestionVote.Value.DISLIKE),
                    distinct=True,
                ),
            )
        )
        params = self.request.query_params
        for param, lookup in [
            ("type", "type"),
            ("status", "status"),
            ("note_id", "target_notes__note_id"),
            ("created_after", "created_at__gte"),
        ]:
            if params.get(param):
                qs = qs.filter(**{lookup: params[param]})

        if author := params.get("author"):
            try:
                qs = qs.filter(author_id=uuid.UUID(author))
            except ValueError:
                qs = qs.filter(author__name__icontains=author)

        if created_before := params.get("created_before"):
            # data sem hora inclui o dia inteiro (FR-022, US5/AC2)
            if parse_date(created_before) and len(created_before) == 10:
                qs = qs.filter(created_at__date__lte=created_before)
            else:
                qs = qs.filter(created_at__lte=created_before)

        submission = params.get("submission")
        if submission == "individual":
            qs = qs.annotate(target_count=Count("target_notes", distinct=True)).filter(
                target_count=1
            )
        elif submission == "bulk":
            qs = qs.annotate(target_count=Count("target_notes", distinct=True)).filter(
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
        if suggestion.author_id == request.user.id:
            # FR-023: o sinal é de terceiros — autor não vota na própria sugestão
            return Response(
                {"detail": "Você não pode votar na própria sugestão."},
                status=status.HTTP_403_FORBIDDEN,
            )
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
        suggestion = _suggestion_for_subscriber(
            self.request, self.kwargs["suggestion_id"]
        )
        return Comment.objects.filter(suggestion=suggestion).select_related("author")

    def perform_create(self, serializer):
        suggestion = _suggestion_for_subscriber(
            self.request, self.kwargs["suggestion_id"]
        )
        serializer.save(author=self.request.user, suggestion=suggestion)
