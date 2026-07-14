"""API de sincronização consumida exclusivamente pelo add-on (contracts/sync.md)."""

from datetime import UTC

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django_ratelimit.core import is_ratelimited
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Deck, DeckModerator, Subscription
from apps.notes.models import MediaFile, Note, NoteType
from apps.notes.sanitize import sanitize_field_values

from . import media


def _publish_rate(_group, _request):
    return settings.RATELIMIT_PUBLISH_RATE


def _media_rate(_group, _request):
    return settings.RATELIMIT_MEDIA_RATE


def _rate_limit_response(request, retry_after: str):
    """T133/FR-052: 429 quando o django-ratelimit marcou a requisição."""
    if getattr(request, "limited", False):
        return Response(
            {"detail": "Limite de requisições atingido. Tente novamente em breve."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": retry_after},
        )
    return None


def _legacy_full_fallback_key(request, deck_id) -> str:
    return f"ankihub-sync-full-fallback:{request.user.auth_id}:{deck_id}"


def _sync_run_is_limited(request, deck_id, *, allow_legacy_fallback=False) -> bool:
    """Permite delta/full do mesmo run e bloqueia outro run por 10s."""
    run_id = request.headers.get("X-Sync-Run-ID")
    if not run_id:  # compatibilidade com clientes anteriores
        fallback_key = _legacy_full_fallback_key(request, deck_id)
        if allow_legacy_fallback and cache.get(fallback_key):
            cache.delete(fallback_key)
            return False
        return is_ratelimited(
            request=request,
            group="sync",
            key="user",
            rate=settings.RATELIMIT_SYNC_RATE,
            increment=True,
        )

    key = f"ankihub-sync-run:{request.user.auth_id}"
    if cache.add(key, run_id, timeout=settings.RATELIMIT_SYNC_WINDOW_SECONDS):
        return False
    return cache.get(key) != run_id


def _note_type_payload(note_type: NoteType) -> dict:
    return {
        "id": str(note_type.id),
        "name": note_type.name,
        "field_names": note_type.field_names,
        "templates": note_type.templates,
        "css": note_type.css,
    }


def _note_payload(note: Note) -> dict:
    return {
        "guid": note.guid,
        "note_type_id": str(note.note_type_id),
        "field_values": note.field_values,
        "tags": note.tags,
        "anki_deck_path": note.anki_deck_path,
        "mod": note.mod.isoformat(),
        "deleted": note.deleted_at is not None,
    }


def _deck_payload(deck: Deck, notes) -> dict:
    note_items = [_note_payload(n) for n in notes]
    return {
        "deck_id": str(deck.id),
        "deck_name": deck.name,
        # ordem de aplicação fixa no add-on: tipos de nota → notas → subdecks (FR-034)
        "note_types": [_note_type_payload(deck.note_type)],
        "notes": note_items,
        "subdecks": sorted(
            {n["anki_deck_path"] for n in note_items if n["anki_deck_path"]}
        ),
        "media": [
            {"filename": m.original_filename, "content_hash": m.content_hash}
            for m in deck.media_files.all()
        ],
    }


class _SubscriberSyncView(APIView):
    """Base delta/full: assinatura + uma execução por usuário a cada 10s."""

    allow_legacy_fallback = False

    def get(self, request, deck_id):
        deck = get_object_or_404(Deck, pk=deck_id)
        if not Subscription.objects.filter(user=request.user, deck=deck).exists():
            return Response(
                {"detail": "Assine o deck para sincronizar."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if _sync_run_is_limited(
            request, deck_id, allow_legacy_fallback=self.allow_legacy_fallback
        ):
            return Response(
                {"detail": "Aguarde 10 segundos entre sincronizações."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "10"},
            )
        return self.sync(request, deck)


class DeltaView(_SubscriberSyncView):
    """GET /decks/{id}/sync/delta/?since_mod= (FR-031, FR-034, FR-035)."""

    def sync(self, request, deck):
        since = None
        since_param = request.query_params.get("since_mod")
        if since_param:
            since = parse_datetime(since_param)
            if since is None:
                return Response(
                    {"detail": "since_mod inválido (use ISO 8601)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if timezone.is_naive(since):
                # datetime.UTC: django.utils.timezone.utc foi removido no Django 5
                since = since.replace(tzinfo=UTC)

        structure_changed_at = deck.note_type.structure_changed_at
        if since and structure_changed_at and structure_changed_at > since:
            # FR-035: mudança estrutural não reconciliável via delta parcial
            if not request.headers.get("X-Sync-Run-ID"):
                cache.set(
                    _legacy_full_fallback_key(request, deck.id),
                    True,
                    timeout=settings.RATELIMIT_SYNC_WINDOW_SECONDS,
                )
            return Response(
                {
                    "deck_id": str(deck.id),
                    "deck_name": deck.name,
                    "full_resync_required": True,
                    "note_types": [],
                    "notes": [],
                    "subdecks": [],
                    "media": [],
                }
            )

        notes = deck.notes.all()
        if since:
            notes = notes.filter(mod__gt=since)
        payload = _deck_payload(deck, notes)
        payload["full_resync_required"] = False
        return Response(payload)


class FullView(_SubscriberSyncView):
    """GET /decks/{id}/sync/full/ — deck completo para ressincronização (FR-035)."""

    allow_legacy_fallback = True

    def sync(self, request, deck):
        return Response(_deck_payload(deck, deck.notes.filter(deleted_at__isnull=True)))


class MediaDownloadView(APIView):
    """GET /media/{content_hash}/ — URL pré-assinada, só se o hash mudou localmente (FR-036)."""

    # rate por minuto largo o suficiente para o fan-out de mídia de um sync run (T133)
    @method_decorator(
        ratelimit(group="media-download", key="user", rate=_media_rate, block=False)
    )
    def get(self, request, content_hash):
        limited = _rate_limit_response(request, retry_after="60")
        if limited:
            return limited
        media_file = MediaFile.objects.filter(
            content_hash=content_hash, deck__subscriptions__user=request.user
        ).first()
        if media_file is None:
            if MediaFile.objects.filter(content_hash=content_hash).exists():
                return Response(
                    {"detail": "Assine o deck para baixar esta mídia."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            return Response(
                {"detail": "Mídia não encontrada."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(
            {
                "url": media.signed_download_url(media_file.storage_path),
                "filename": media_file.original_filename,
            }
        )


class PublishView(APIView):
    """POST /decks/{id}/publish/ — importação inicial de um deck (T035).

    O add-on gera o UUID do deck no primeiro publish; o criador vira o
    moderador original. Depois disso, a web é a única fonte de mudanças.
    """

    @method_decorator(
        ratelimit(
            group="deck-publish",
            key="user",
            rate=_publish_rate,
            method="POST",
            block=False,
        )
    )
    def post(self, request, deck_id):
        limited = _rate_limit_response(request, retry_after="3600")
        if limited:
            return limited
        data = request.data
        note_type_data = data.get("note_type") or {}
        if not data.get("name") or not note_type_data.get("field_names"):
            return Response(
                {"detail": "Payload requer name e note_type.field_names."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Deck.objects.filter(pk=deck_id).exists():
            return Response(
                {
                    "detail": (
                        "O deck já foi importado; alterações devem passar pela web "
                        "e pelo fluxo de sugestões."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )

        now = timezone.now()
        with transaction.atomic():
            note_type = NoteType.objects.create(
                name=note_type_data.get("name", "Básico"),
                field_names=note_type_data["field_names"],
                templates=note_type_data.get("templates", []),
                css=note_type_data.get("css", ""),
            )
            deck = Deck.objects.create(
                id=deck_id,
                name=data["name"],
                description=data.get("description", ""),
                subject_tags=data.get("subject_tags", []),
                note_type=note_type,
            )
            DeckModerator.objects.create(deck=deck, user=request.user, status="active")

            for item in data.get("notes", []):
                fields = sanitize_field_values(item.get("field_values", {}))  # FR-015
                Note.objects.create(
                    deck=deck,
                    note_type=note_type,
                    guid=item["guid"],
                    field_values=fields,
                    tags=item.get("tags", []),
                    anki_deck_path=item.get("anki_deck_path", ""),
                    mod=now,
                )

            deck.note_count = deck.notes.filter(deleted_at__isnull=True).count()
            deck.save()

            upload_urls = {}
            for item in data.get("media", []):
                media_file, created = MediaFile.objects.get_or_create(
                    deck=deck,
                    content_hash=item["content_hash"],
                    defaults={
                        "original_filename": item["filename"],
                        "storage_path": f"{deck.id}/{item['content_hash']}",
                    },
                )
                if created:  # hash inédito → precisa de upload
                    upload_urls[item["content_hash"]] = media.signed_upload_url(
                        media_file.storage_path
                    )

        return Response(
            {
                "deck_id": str(deck.id),
                "note_count": deck.note_count,
                "media_upload_urls": upload_urls,
            },
            status=status.HTTP_201_CREATED,
        )
