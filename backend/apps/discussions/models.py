from django.db import models
from django.db.models import Q

from apps.base import BaseModel


class Comment(BaseModel):
    """Comentário na thread geral da nota (US-04) OU na thread de uma sugestão (US-09).

    Invariante: exatamente um entre `note` e `suggestion` é não nulo — as duas
    threads nunca se misturam (FR-024, data-model.md).
    """

    author = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="comments"
    )
    body = models.TextField()
    note = models.ForeignKey(
        "notes.Note",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )
    suggestion = models.ForeignKey(
        "suggestions.Suggestion",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="comments",
    )
    edited_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(note__isnull=False, suggestion__isnull=True)
                | Q(note__isnull=True, suggestion__isnull=False),
                name="comment_note_xor_suggestion",
            )
        ]
