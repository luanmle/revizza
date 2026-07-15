from django.conf import settings
from rest_framework import serializers

from .models import Note, NoteType


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

    class Meta:
        model = Note
        fields = ["id", "field_values", "tags"]


class NoteTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoteType
        fields = ["id", "name", "field_names", "templates", "css"]


class NoteDetailSerializer(serializers.ModelSerializer):
    """Detalhe da nota: o suficiente para o preview isolado em iframe (FR-011)."""

    note_type = NoteTypeSerializer()

    class Meta:
        model = Note
        fields = ["id", "deck", "field_values", "tags", "note_type"]
