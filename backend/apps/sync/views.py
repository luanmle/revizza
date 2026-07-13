"""API de sincronização consumida exclusivamente pelo add-on (contracts/sync.md)."""

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django_ratelimit.core import is_ratelimited
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Deck, DeckModerator, Subscription
from apps.notes.models import MediaFile, Note, NoteType
from apps.notes.sanitize import sanitize_field_values

from . import media


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
    """Base delta/full: exige assinatura e aplica o rate limit de 10s (FR-032).

    O grupo de rate limit é por endpoint (delta e full separados): o fallback
    delta→full_resync_required→full precisa das duas chamadas em sequência;
    duas tentativas de *sincronizar* (dois deltas) continuam bloqueadas.
    """

    rate_group = ""

    def get(self, request, deck_id):
        deck = get_object_or_404(Deck, pk=deck_id)
        if not Subscription.objects.filter(user=request.user, deck=deck).exists():
            return Response(
                {"detail": "Assine o deck para sincronizar."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if is_ratelimited(
            request=request,
            group=self.rate_group,
            key="user",
            rate=settings.RATELIMIT_SYNC_RATE,
            increment=True,
        ):
            return Response(
                {"detail": "Aguarde 10 segundos entre sincronizações."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": "10"},
            )
        return self.sync(request, deck)


class DeltaView(_SubscriberSyncView):
    """GET /decks/{id}/sync/delta/?since_mod= (FR-031, FR-034, FR-035)."""

    rate_group = "sync-delta"

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
                since = timezone.make_aware(since, timezone.utc)

        structure_changed_at = deck.note_type.structure_changed_at
        if since and structure_changed_at and structure_changed_at > since:
            # FR-035: mudança estrutural não reconciliável via delta parcial
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

    rate_group = "sync-full"

    def sync(self, request, deck):
        return Response(_deck_payload(deck, deck.notes.filter(deleted_at__isnull=True)))


class MediaDownloadView(APIView):
    """GET /media/{content_hash}/ — URL pré-assinada, só se o hash mudou localmente (FR-036)."""

    def get(self, request, content_hash):
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
    """POST /decks/{id}/publish/ — upload inicial/re-publish de um deck (T035).

    O add-on gera o UUID do deck no primeiro publish; o criador vira o
    moderador original. Re-publish exige moderador ativo.
    """

    def post(self, request, deck_id):
        data = request.data
        note_type_data = data.get("note_type") or {}
        if not data.get("name") or not note_type_data.get("field_names"):
            return Response(
                {"detail": "Payload requer name e note_type.field_names."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deck = Deck.objects.filter(pk=deck_id).first()
        if (
            deck
            and not DeckModerator.objects.filter(
                deck=deck, user=request.user, status="active"
            ).exists()
        ):
            return Response(
                {"detail": "Apenas moderadores podem publicar neste deck."},
                status=status.HTTP_403_FORBIDDEN,
            )

        now = timezone.now()
        with transaction.atomic():
            if deck is None:
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
                DeckModerator.objects.create(
                    deck=deck, user=request.user, status="active"
                )
            else:
                note_type = deck.note_type
                new_templates = note_type_data.get("templates", note_type.templates)
                if len(new_templates) != len(note_type.templates):
                    note_type.structure_changed_at = now  # FR-035
                note_type.name = note_type_data.get("name", note_type.name)
                note_type.field_names = note_type_data["field_names"]
                note_type.templates = new_templates
                note_type.css = note_type_data.get("css", note_type.css)
                note_type.save()
                deck.name = data["name"]
                deck.description = data.get("description", deck.description)
                deck.subject_tags = data.get("subject_tags", deck.subject_tags)

            existing = {n.guid: n for n in deck.notes.all()}
            for item in data.get("notes", []):
                fields = sanitize_field_values(item.get("field_values", {}))  # FR-015
                tags = item.get("tags", [])
                path = item.get("anki_deck_path", "")
                note = existing.get(item["guid"])
                if note is None:
                    Note.objects.create(
                        deck=deck,
                        note_type=note_type,
                        guid=item["guid"],
                        field_values=fields,
                        tags=tags,
                        anki_deck_path=path,
                        mod=now,
                    )
                elif (note.field_values, note.tags, note.anki_deck_path) != (
                    fields,
                    tags,
                    path,
                ) or note.deleted_at is not None:
                    note.field_values = fields
                    note.tags = tags
                    note.anki_deck_path = path
                    note.deleted_at = None
                    note.mod = now  # entra no próximo delta dos assinantes
                    note.save()

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
