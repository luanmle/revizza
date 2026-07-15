"""Lógica compartilhada entre serializers (data-model.md — estado derivado de sync)."""

from typing import Literal

from apps.notifications.models import Notification

from .models import Deck, Subscription

SyncState = Literal["not_synced_yet", "up_to_date", "out_of_date"]


def deck_sync_state(user, deck: Deck) -> SyncState | None:
    """Único ponto que deriva o estado de sync pendente (FR-007).

    `None` se não inscrito. Fonte única para `DeckDetailSerializer.sync_status`
    (US1/US2) e `DeckSubscribedSerializer.pending_sync` (US3).
    """
    subscription = Subscription.objects.filter(user=user, deck=deck).first()
    if subscription is None:
        return None
    if subscription.last_synced_at is None:
        return "not_synced_yet"
    has_pending = Notification.objects.filter(
        recipient=user,
        deck=deck,
        type=Notification.Type.SYNC_PENDING,
        resolved_at__isnull=True,
    ).exists()
    return "out_of_date" if has_pending else "up_to_date"
