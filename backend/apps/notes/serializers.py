import re

from django.conf import settings
from rest_framework import serializers

from apps.sync import media

from .models import MediaFile, Note, NoteType

_IMG_SRC = re.compile(r'src=(["\'])(.*?)\1')


def resolve_media_refs(field_values: dict, deck_id) -> dict:
    """Reescreve <img src="nome_original"> para a URL assinada do Storage.

    A nota guarda o nome de arquivo local do Anki (ex.: `lion.jpg`), que não é
    URL nenhuma no web. Cada nome referenciado é mapeado via MediaFile(deck,
    original_filename) para uma URL assinada, para o preview renderizar a imagem.
    """
    referenced = {m.group(2) for v in field_values.values() for m in _IMG_SRC.finditer(v)}
    if not referenced:
        return field_values
    # ponytail: assina um por vez (chamada de rede cada). Suficiente para o
    # detalhe de uma nota; se a listagem ficar lenta, trocar por create_signed_urls.
    url_by_name = {
        mf.original_filename: media.signed_download_url(mf.storage_path)
        for mf in MediaFile.objects.filter(
            deck_id=deck_id, status="ready", original_filename__in=referenced
        )
    }
    if not url_by_name:
        return field_values

    def _sub(match):
        quote, name = match.group(1), match.group(2)
        url = url_by_name.get(name)
        return f"src={quote}{url}{quote}" if url else match.group(0)

    return {key: _IMG_SRC.sub(_sub, value) for key, value in field_values.items()}


class NoteResolveSerializer(serializers.Serializer):
    """GUID → ids + URLs web, para o botão "Sugerir mudança" do add-on (US2)."""

    note_id = serializers.UUIDField(source="id")
    deck_id = serializers.UUIDField()
    web_url = serializers.SerializerMethodField()
    history_url = serializers.SerializerMethodField()

    def get_web_url(self, note):
        return f"{settings.FRONTEND_BASE_URL}/decks/{note.deck_id}/notes/{note.id}"

    def get_history_url(self, note):
        return (
            f"{settings.FRONTEND_BASE_URL}/decks/{note.deck_id}"
            f"/suggestions?note_id={note.id}"
        )


class NoteListSerializer(serializers.ModelSerializer):
    """Item do resultado de busca (FR-010) — leve, sem note type."""

    field_values = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = ["id", "field_values", "tags"]

    def get_field_values(self, note):
        return resolve_media_refs(note.field_values, note.deck_id)


class NoteTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoteType
        fields = ["id", "name", "field_names", "templates", "css"]


class NoteDetailSerializer(serializers.ModelSerializer):
    """Detalhe da nota: o suficiente para o preview isolado em iframe (FR-011)."""

    note_type = NoteTypeSerializer()
    field_values = serializers.SerializerMethodField()

    class Meta:
        model = Note
        fields = ["id", "deck", "field_values", "tags", "note_type"]

    def get_field_values(self, note):
        return resolve_media_refs(note.field_values, note.deck_id)
