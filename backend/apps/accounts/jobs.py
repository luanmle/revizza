"""Jobs periódicos de privacidade; executáveis sem fila externa (FR-046)."""

from datetime import timedelta

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.catalog.models import Deck

from . import supabase_gateway
from .models import User

DELETION_GRACE_PERIOD = timedelta(days=7)


def delete_expired_accounts(now=None) -> int:
    """Apaga contas cuja carência venceu; falha remota mantém o perfil para retry."""
    cutoff = (now or timezone.now()) - DELETION_GRACE_PERIOD
    candidate_ids = list(
        User.objects.filter(deletion_requested_at__lte=cutoff).values_list(
            "pk", flat=True
        )
    )
    deleted = 0
    for user_id in candidate_ids:
        with transaction.atomic():
            user = (
                User.objects.select_for_update()
                .filter(pk=user_id, deletion_requested_at__lte=cutoff)
                .first()
            )
            if not user:
                continue
            subscribed_decks = list(
                user.subscriptions.values_list("deck_id", flat=True)
            )
            supabase_gateway.delete_user(str(user.auth_id))
            user.delete()
            Deck.objects.filter(
                pk__in=subscribed_decks, subscriber_count__gt=0
            ).update(subscriber_count=F("subscriber_count") - 1)
            deleted += 1
    return deleted
