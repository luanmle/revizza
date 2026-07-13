"""Regras de acesso de moderação (FR-025): só moderador ativo decide sugestão."""

from apps.catalog.models import DeckModerator


def is_active_deck_moderator(user, deck) -> bool:
    return DeckModerator.objects.filter(
        deck=deck, user=user, status=DeckModerator.Status.ACTIVE
    ).exists()
