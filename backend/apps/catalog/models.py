from django.db import models

from apps.base import BaseModel


class Deck(BaseModel):
    creator = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_decks",
    )
    name = models.CharField(max_length=200)
    anki_deck_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    subject_tags = models.JSONField(default=list)  # filtro do catálogo (FR-007)
    # sem FK de tipo de nota: um deck pode ter N tipos, derivados das suas notas via
    # NoteType.objects.filter(notes__deck=deck).distinct() (research.md Decisão 1)
    note_count = models.PositiveIntegerField(default=0)  # denormalizado
    subscriber_count = models.PositiveIntegerField(default=0)  # denormalizado
    is_official = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name


class DeckModerator(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending"
        ACTIVE = "active"

    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name="moderators")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="moderated_decks"
    )
    invited_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    status = models.CharField(
        max_length=8, choices=Status.choices, default=Status.PENDING
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deck", "user"], name="unique_deck_moderator"
            )
        ]


class Subscription(BaseModel):
    """Vínculo usuário↔deck que habilita a sincronização (FR-009, data-model.md)."""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="subscriptions"
    )
    deck = models.ForeignKey(
        Deck, on_delete=models.CASCADE, related_name="subscriptions"
    )
    # gatilhos configuráveis, não mutuamente exclusivos (US-08/FR-031)
    sync_trigger_manual = models.BooleanField(default=True)
    sync_trigger_on_anki_open = models.BooleanField(default=False)
    sync_trigger_chained_native = models.BooleanField(default=False)
    # FR-037: apagar de fato vs. apenas marcar ao propagar remoção
    delete_notes_on_removal = models.BooleanField(default=False)
    # None = nunca sincronizou este deck desde a inscrição (data-model.md)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "deck"], name="unique_subscription")
        ]
