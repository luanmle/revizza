from django.db import models

from apps.base import BaseModel


class ProtectedFieldConfig(BaseModel):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="protected_fields"
    )
    deck = models.ForeignKey(
        "catalog.Deck", on_delete=models.CASCADE, related_name="protected_fields"
    )
    field_name = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "deck", "field_name"],
                name="unique_protected_field_per_user_deck",
            )
        ]


class ProtectedTagConfig(BaseModel):
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="protected_tags"
    )
    deck = models.ForeignKey(
        "catalog.Deck", on_delete=models.CASCADE, related_name="protected_tags"
    )
    tag = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "deck", "tag"],
                name="unique_protected_tag_per_user_deck",
            )
        ]
