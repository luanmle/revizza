from rest_framework import serializers

from apps.notes.sanitize import sanitize_field_values

from .models import Suggestion


class ChangeSuggestionSerializer(serializers.ModelSerializer):
    """Entrada/saída da sugestão de mudança (FR-013 a FR-016)."""

    # FR-013: categoria estruturada obrigatória em sugestão de mudança
    change_category = serializers.ChoiceField(choices=Suggestion.ChangeCategory.choices)
    proposed_field_values = serializers.DictField(
        child=serializers.CharField(allow_blank=True), required=False
    )
    note_ids = serializers.SerializerMethodField()

    class Meta:
        model = Suggestion
        fields = [
            "id",
            "type",
            "deck",
            "status",
            "change_category",
            "justification",
            "proposed_field_values",
            "note_ids",
            "created_at",
        ]
        read_only_fields = ["id", "type", "deck", "status", "note_ids", "created_at"]

    def validate_proposed_field_values(self, value):
        # FR-015: nunca confiar no client — todo HTML passa pelo nh3 antes de persistir
        return sanitize_field_values(value)

    def get_note_ids(self, suggestion) -> list[str]:
        return [
            str(note_id)
            for note_id in suggestion.target_notes.values_list("note_id", flat=True)
        ]


class BulkChangeSuggestionSerializer(ChangeSuggestionSerializer):
    """Mesma sugestão de mudança aplicada a várias notas de uma vez (FR-017)."""

    note_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, write_only=True
    )
