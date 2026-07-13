from rest_framework import serializers

from .models import Note, NoteType


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
