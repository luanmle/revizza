"""Busca e detalhe de notas (contracts/notes.md, FR-010, FR-011)."""

import uuid

from django.conf import settings
from django.db.models import Q, TextField
from django.db.models.functions import Cast
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View
from rest_framework import generics
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.base import json_text_forms
from apps.catalog.models import Deck, Subscription
from config.pagination import DefaultCursorPagination

from .models import Note
from .serializers import (
    NoteDetailSerializer,
    NoteListSerializer,
    NoteResolveSerializer,
)


def _require_subscription(user, deck):
    if not Subscription.objects.filter(user=user, deck=deck).exists():
        raise PermissionDenied("Assine o deck para acessar as notas.")


def note_by_guid(guid):
    """Resolve o GUID estável do Anki para a Nota não deletada (404 se ausente).

    ponytail: GUID é único global no Anki; se dois decks colidirem, pega o mais
    recente — troca por unique global se o import passar a garantir isso.
    """
    note = (
        Note.objects.select_related("deck")
        .filter(guid=guid, deleted_at__isnull=True)
        .order_by("-mod")
        .first()
    )
    if note is None:
        raise Http404("Nota não encontrada.")
    return note


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
    """GET /notes/{id}/ — campos + note type (templates/css) para o preview (FR-011).

    Leitura pública (US1): a página web da nota abre a partir do add-on sem login.
    Escritas continuam em views próprias com auth + assinatura.
    """

    serializer_class = NoteDetailSerializer
    permission_classes = [AllowAny]

    def get_object(self):
        return get_object_or_404(
            Note.objects.select_related("note_type", "deck"),
            pk=self.kwargs["note_id"],
            deleted_at__isnull=True,
        )


class NoteResolveView(APIView):
    """GET /notes/resolve/?guid= — ids + URLs da nota (auth, US2 submit flow)."""

    def get(self, request):
        guid = request.query_params.get("guid")
        if not guid:
            return Response(
                {"guid": ["Parâmetro obrigatório."]},
                status=400,
            )
        try:
            note = note_by_guid(guid)
        except Http404:
            raise NotFound("Nota não encontrada.")
        return Response(NoteResolveSerializer(note).data)


class GuidRedirectView(View):
    """GET /go/note/<guid>/ — redireciona o navegador para a página da nota (US1).

    Público: aberto pelo botão "Ver no Revizza" do revisor. GUID desconhecido
    cai na página amigável /nota-nao-encontrada (nunca JSON cru, US1 AS#3).
    """

    def get(self, request, guid):
        try:
            note = note_by_guid(guid)
        except Http404:
            return HttpResponseRedirect(f"{settings.FRONTEND_BASE_URL}/nota-nao-encontrada")
        return HttpResponseRedirect(
            f"{settings.FRONTEND_BASE_URL}/decks/{note.deck_id}/notes/{note.id}"
        )


class GuidHistoryRedirectView(View):
    """GET /go/note/<guid>/history/ — redireciona ao histórico de sugestões (US3).

    Público: botão "Ver histórico" do revisor. GUID desconhecido cai na mesma
    página amigável /nota-nao-encontrada do T007.
    """

    def get(self, request, guid):
        try:
            note = note_by_guid(guid)
        except Http404:
            return HttpResponseRedirect(f"{settings.FRONTEND_BASE_URL}/nota-nao-encontrada")
        return HttpResponseRedirect(
            f"{settings.FRONTEND_BASE_URL}/decks/{note.deck_id}"
            f"/suggestions?note_id={note.id}"
        )
