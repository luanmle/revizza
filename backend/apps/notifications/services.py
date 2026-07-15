from .models import Notification


def notify_suggestion_decided(suggestion) -> None:
    """Notifica o autor do accept/reject e, em accept, os assinantes (sync_pending). FR-001/FR-005."""
    if suggestion.author_id is not None:
        target_notes = list(suggestion.target_notes.all())
        note = target_notes[0].note if len(target_notes) == 1 else None
        notif_type = (
            Notification.Type.SUGGESTION_ACCEPTED
            if suggestion.status == suggestion.Status.ACCEPTED
            else Notification.Type.SUGGESTION_REJECTED
        )
        Notification.objects.create(
            recipient=suggestion.author,
            type=notif_type,
            deck=suggestion.deck,
            suggestion=suggestion,
            note=note,
        )

    if suggestion.status == suggestion.Status.ACCEPTED:
        from apps.catalog.models import Subscription

        subscriber_ids = Subscription.objects.filter(
            deck=suggestion.deck
        ).values_list("user_id", flat=True)
        for uid in subscriber_ids:
            Notification.objects.get_or_create(
                recipient_id=uid,
                deck=suggestion.deck,
                type=Notification.Type.SYNC_PENDING,
                resolved_at__isnull=True,
                defaults={},
            )


def notify_new_suggestion(suggestion) -> None:
    """Notifica moderadores ativos do deck sobre nova sugestão, exceto o autor. FR-003."""
    from apps.catalog.models import DeckModerator

    recipient_ids = (
        DeckModerator.objects.filter(
            deck=suggestion.deck, status=DeckModerator.Status.ACTIVE
        )
        .exclude(user=suggestion.author)
        .values_list("user_id", flat=True)
    )
    Notification.objects.bulk_create(
        Notification(
            recipient_id=uid,
            type=Notification.Type.NEW_SUGGESTION,
            deck=suggestion.deck,
            suggestion=suggestion,
        )
        for uid in recipient_ids
    )
