from django.db import models

from apps.base import BaseModel


class NoteType(BaseModel):
    """Mapeia `notetypes`/`models` nativo do Anki (data-model.md)."""

    name = models.CharField(max_length=200)
    field_names = models.JSONField(
        default=list
    )  # ordem preservada — nunca reordenar (US-08)
    templates = models.JSONField(
        default=list
    )  # mudança no nº de templates força full resync
    css = models.TextField(blank=True)
    # FR-035: marcado quando o nº de templates muda em re-publish; o delta
    # responde full_resync_required=true para quem sincronizou antes disso
    structure_changed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.name


class Note(BaseModel):
    """Mapeia `notes` nativo do Anki; `mod` é o marcador do delta de sync (FR-034)."""

    deck = models.ForeignKey(
        "catalog.Deck", on_delete=models.CASCADE, related_name="notes"
    )
    note_type = models.ForeignKey(
        NoteType, on_delete=models.PROTECT, related_name="notes"
    )
    field_values = models.JSONField(default=dict)  # {campo: html já sanitizado via nh3}
    tags = models.JSONField(default=list)
    guid = models.CharField(
        max_length=64
    )  # GUID estável compatível com o formato do Anki
    # FR-034: posição no subdeck relativa ao deck raiz ("" = raiz; "A::B" = subdeck)
    anki_deck_path = models.CharField(max_length=500, blank=True, default="")
    mod = models.DateTimeField()
    deleted_at = models.DateTimeField(null=True, blank=True)  # soft-delete (US-07)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deck", "guid"], name="unique_note_guid_per_deck"
            )
        ]
        indexes = [models.Index(fields=["deck", "mod"])]  # consulta do delta since_mod


class MediaFile(BaseModel):
    """Mídia (imagem) referenciada em campos, deduplicada por hash (FR-036)."""

    STATUS_CHOICES = (
        ("pending_upload", "Pending upload"),
        ("ready", "Ready"),
    )

    deck = models.ForeignKey(
        "catalog.Deck", on_delete=models.CASCADE, related_name="media_files"
    )
    content_hash = models.CharField(max_length=64)  # sha256
    storage_path = models.CharField(max_length=500)  # caminho no Supabase Storage
    original_filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="ready"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deck", "content_hash"], name="unique_media_hash_per_deck"
            )
        ]
