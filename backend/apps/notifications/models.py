from django.db import models

from apps.base import BaseModel


class Notification(BaseModel):
    """Notificação in-app de decisão/sugestão/sync (data-model.md)."""

    class Type(models.TextChoices):
        SUGGESTION_ACCEPTED = "suggestion_accepted"
        SUGGESTION_REJECTED = "suggestion_rejected"
        NEW_SUGGESTION = "new_suggestion"
        SYNC_PENDING = "sync_pending"

    recipient = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="notifications"
    )
    type = models.CharField(max_length=19, choices=Type.choices)
    deck = models.ForeignKey(
        "catalog.Deck", on_delete=models.CASCADE, related_name="notifications"
    )
    suggestion = models.ForeignKey(
        "suggestions.Suggestion",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    note = models.ForeignKey(
        "notes.Note",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    read_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["recipient", "read_at", "created_at"],
                name="notif_recipient_unread_idx",
            )
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "deck"],
                condition=models.Q(
                    type="sync_pending", resolved_at__isnull=True
                ),
                name="unique_active_sync_pending_per_recipient_deck",
            )
        ]
