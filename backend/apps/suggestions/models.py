from django.db import models

from apps.base import BaseModel


class Suggestion(BaseModel):
    """Sugestão de mudança/nota nova/exclusão, sempre decidida por moderador (data-model.md)."""

    class Type(models.TextChoices):
        CHANGE = "change"
        NEW_NOTE = "new_note"
        DELETION = "deletion"

    class ChangeCategory(models.TextChoices):
        CONTEUDO_ATUALIZADO = "conteudo_atualizado", "Conteúdo atualizado"
        ORTOGRAFIA_GRAMATICA = "ortografia_gramatica", "Ortografia/Gramática"
        ERRO_CONTEUDO = "erro_conteudo", "Erro de conteúdo"
        NOVA_TAG = "nova_tag", "Nova tag"
        TAG_ATUALIZADA = "tag_atualizada", "Tag atualizada"
        OUTRO = "outro", "Outro"

    class Status(models.TextChoices):
        PENDING = "pending"
        ACCEPTED = "accepted"
        REJECTED = "rejected"

    type = models.CharField(max_length=10, choices=Type.choices)
    deck = models.ForeignKey(
        "catalog.Deck", on_delete=models.CASCADE, related_name="suggestions"
    )
    author = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="suggestions",
    )
    # obrigatório apenas quando type=change (FR-013) — validado no serializer
    change_category = models.CharField(
        max_length=20, choices=ChangeCategory.choices, null=True, blank=True
    )
    justification = models.TextField()  # obrigatória em todos os tipos
    proposed_field_values = models.JSONField(
        null=True, blank=True
    )  # {campo: html sanitizado via nh3}; usado em change/new_note
    proposed_tags = models.JSONField(default=list, blank=True)
    # terminal ao sair de pending — sem reversão via UI (FR-027)
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.PENDING
    )
    rejection_reason = models.TextField(null=True, blank=True)
    decided_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        indexes = [models.Index(fields=["deck", "status"])]  # filtros da tela (FR-021)


class SuggestionVote(BaseModel):
    """Curtida/descurtida em sugestão — um voto por usuário, upsert (FR-023)."""

    class Value(models.TextChoices):
        LIKE = "like"
        DISLIKE = "dislike"

    suggestion = models.ForeignKey(
        Suggestion, on_delete=models.CASCADE, related_name="votes"
    )
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="suggestion_votes"
    )
    value = models.CharField(max_length=7, choices=Value.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["suggestion", "user"], name="unique_vote_per_user"
            )
        ]


class SuggestionTargetNote(BaseModel):
    """Junção: uma Suggestion `change` pode cobrir várias notas (sugestão em lote, FR-017)."""

    suggestion = models.ForeignKey(
        Suggestion, on_delete=models.CASCADE, related_name="target_notes"
    )
    note = models.ForeignKey(
        "notes.Note", on_delete=models.CASCADE, related_name="suggestion_targets"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["suggestion", "note"], name="unique_suggestion_target_note"
            )
        ]
