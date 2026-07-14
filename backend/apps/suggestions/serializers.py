from html import unescape

from django.utils.html import strip_tags
from rest_framework import serializers

from apps.notes.models import NoteType
from apps.notes.sanitize import sanitize_field_values

from .models import Suggestion, SuggestionVote


def empty_field_names(field_values: dict[str, str] | None) -> list[str]:
    """Campos sem texto visível, mantendo a ordem enviada pelo tipo de nota."""
    return [
        field
        for field, value in (field_values or {}).items()
        if not unescape(strip_tags(value)).replace("\xa0", "").strip()
    ]


def _note_ids(suggestion) -> list[str]:
    # itera a relação (usa o prefetch da view) em vez de values_list, que re-consulta
    return [str(target.note_id) for target in suggestion.target_notes.all()]


def _clean_tags(value: list[str]) -> list[str]:
    tags = [tag.strip() for tag in value]
    if any(not tag for tag in tags):
        raise serializers.ValidationError("Tags não podem ser vazias.")
    return list(dict.fromkeys(tags))


class ChangeSuggestionSerializer(serializers.ModelSerializer):
    """Entrada/saída da sugestão de mudança (FR-013 a FR-016)."""

    # FR-013: categoria estruturada obrigatória em sugestão de mudança
    change_category = serializers.ChoiceField(choices=Suggestion.ChangeCategory.choices)
    proposed_field_values = serializers.DictField(
        child=serializers.CharField(allow_blank=True), required=False
    )
    # FR-013 (Nova tag/Tag atualizada): tags propostas junto com (ou no lugar de) campos
    tags = serializers.ListField(
        source="proposed_tags",
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
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
            "tags",
            "note_ids",
            "created_at",
        ]
        read_only_fields = ["id", "type", "deck", "status", "note_ids", "created_at"]

    def validate_proposed_field_values(self, value):
        # FR-015: nunca confiar no client — todo HTML passa pelo nh3 antes de persistir
        return sanitize_field_values(value)

    def validate_tags(self, value):
        return _clean_tags(value)

    def get_note_ids(self, suggestion) -> list[str]:
        return _note_ids(suggestion)


class BulkChangeSuggestionSerializer(ChangeSuggestionSerializer):
    """Mesma sugestão de mudança aplicada a várias notas de uma vez (FR-017)."""

    note_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1, write_only=True
    )


class NewNoteSuggestionSerializer(serializers.ModelSerializer):
    proposed_field_values = serializers.DictField(
        child=serializers.CharField(allow_blank=True)
    )
    tags = serializers.ListField(
        source="proposed_tags",
        child=serializers.CharField(max_length=100),
        allow_empty=False,
    )
    # obrigatório só quando o deck tem 2+ tipos; resolvido automaticamente se tem um só
    note_type = serializers.PrimaryKeyRelatedField(
        queryset=NoteType.objects.all(), required=False
    )
    note_ids = serializers.SerializerMethodField()
    empty_fields = serializers.SerializerMethodField()

    class Meta:
        model = Suggestion
        fields = [
            "id",
            "type",
            "deck",
            "status",
            "note_type",
            "justification",
            "proposed_field_values",
            "tags",
            "empty_fields",
            "note_ids",
            "created_at",
        ]
        read_only_fields = ["id", "type", "deck", "status", "created_at"]

    def validate_proposed_field_values(self, value):
        return sanitize_field_values(value)

    def validate_tags(self, value):
        return _clean_tags(value)

    def validate(self, attrs):
        note_type = self._resolve_note_type(attrs)
        attrs["note_type"] = note_type
        values = attrs["proposed_field_values"]
        expected = note_type.field_names
        missing = [field for field in expected if field not in values]
        unknown = [field for field in values if field not in expected]
        if missing or unknown:
            detail = []
            if missing:
                detail.append(f"Campos ausentes: {', '.join(missing)}.")
            if unknown:
                detail.append(f"Campos desconhecidos: {', '.join(unknown)}.")
            raise serializers.ValidationError(
                {"proposed_field_values": " ".join(detail)}
            )
        return attrs

    def _resolve_note_type(self, attrs):
        """Escolhe o tipo de nota da sugestão: exigido se o deck tem 2+, auto se tem 1."""
        deck = self.context["deck"]
        deck_types = list(
            NoteType.objects.filter(
                notes__deck=deck, notes__deleted_at__isnull=True
            ).distinct()
        )
        note_type = attrs.get("note_type")
        if note_type is None:
            if len(deck_types) == 1:
                return deck_types[0]
            raise serializers.ValidationError(
                {"note_type": "Escolha o tipo de nota (o deck tem mais de um)."}
            )
        if deck_types and note_type not in deck_types:
            raise serializers.ValidationError(
                {"note_type": "Tipo de nota não pertence a este deck."}
            )
        return note_type

    def get_note_ids(self, suggestion) -> list[str]:
        return _note_ids(suggestion)

    def get_empty_fields(self, suggestion) -> list[str]:
        return empty_field_names(suggestion.proposed_field_values)


class DeletionSuggestionSerializer(serializers.ModelSerializer):
    note_ids = serializers.SerializerMethodField()

    class Meta:
        model = Suggestion
        fields = [
            "id",
            "type",
            "deck",
            "status",
            "justification",
            "note_ids",
            "created_at",
        ]
        read_only_fields = ["id", "type", "deck", "status", "created_at"]

    def get_note_ids(self, suggestion) -> list[str]:
        return _note_ids(suggestion)


class SuggestionDetailSerializer(serializers.ModelSerializer):
    """Saída da lista/detalhe da tela de Community Suggestions (FR-020 a FR-022)."""

    note_ids = serializers.SerializerMethodField()
    # counts vêm do annotate da lista (FR-054); fallback consulta por instância (detalhe)
    likes_count = serializers.SerializerMethodField()
    dislikes_count = serializers.SerializerMethodField()
    tags = serializers.ListField(source="proposed_tags", read_only=True)
    empty_fields = serializers.SerializerMethodField()
    author_name = serializers.SerializerMethodField()
    note_context = serializers.SerializerMethodField()

    class Meta:
        model = Suggestion
        fields = [
            "id",
            "type",
            "deck",
            "status",
            "author",
            "author_name",
            "change_category",
            "justification",
            "proposed_field_values",
            "tags",
            "empty_fields",
            "note_ids",
            "note_context",
            "likes_count",
            "dislikes_count",
            "rejection_reason",
            "created_at",
        ]

    def get_note_ids(self, suggestion) -> list[str]:
        return _note_ids(suggestion)

    def get_author_name(self, suggestion):
        return suggestion.author.name or None if suggestion.author else None

    def get_note_context(self, suggestion) -> list[dict]:
        context = []
        for target in suggestion.target_notes.all():
            open_count = getattr(target, "open_suggestion_count", None)
            if open_count is None:
                open_count = target.note.suggestion_targets.filter(
                    suggestion__status=Suggestion.Status.PENDING
                ).count()
            context.append(
                {
                    "id": str(target.note_id),
                    "field_values": target.note.field_values,
                    "tags": target.note.tags,
                    "open_suggestion_count": open_count,
                }
            )
        return context

    def get_likes_count(self, suggestion) -> int:
        annotated = getattr(suggestion, "likes", None)
        if annotated is not None:
            return annotated
        return suggestion.votes.filter(value=SuggestionVote.Value.LIKE).count()

    def get_dislikes_count(self, suggestion) -> int:
        annotated = getattr(suggestion, "dislikes", None)
        if annotated is not None:
            return annotated
        return suggestion.votes.filter(value=SuggestionVote.Value.DISLIKE).count()

    def get_empty_fields(self, suggestion) -> list[str]:
        return empty_field_names(suggestion.proposed_field_values)


class SuggestionVoteSerializer(serializers.Serializer):
    value = serializers.ChoiceField(choices=SuggestionVote.Value.choices)
