import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.catalog.models import Subscription


pytestmark = pytest.mark.django_db


@override_settings(RATELIMIT_SUGGESTION_RATE="1/m")
def test_suggestion_submission_limit_is_shared_across_endpoints(
    auth_client, user, make_note
):
    cache.clear()
    note = make_note()
    Subscription.objects.create(user=user, deck=note.deck)

    first = auth_client.post(
        f"/api/v1/notes/{note.id}/suggestions/change/",
        {
            "change_category": "erro_conteudo",
            "justification": "Correção necessária.",
            "proposed_field_values": {"Frente": "Pergunta corrigida"},
        },
        format="json",
    )
    second = auth_client.post(
        f"/api/v1/decks/{note.deck_id}/suggestions/new-note/",
        {},
        format="json",
    )

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "60"
