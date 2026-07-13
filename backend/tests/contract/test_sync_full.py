"""Contract test: GET /decks/{id}/sync/full/ (contracts/sync.md, FR-035)."""

import pytest
from django.utils import timezone

from apps.catalog.models import Subscription
from apps.notes.models import Note

pytestmark = pytest.mark.django_db


def test_full_returns_complete_live_deck(auth_client, user, make_deck):
    deck = make_deck(name="Deck Completo")
    Subscription.objects.create(user=user, deck=deck)
    now = timezone.now()
    Note.objects.create(
        deck=deck,
        note_type=deck.note_type,
        guid="viva",
        field_values={"Frente": "Q", "Verso": "A"},
        anki_deck_path="Capítulo 1",
        mod=now,
    )
    Note.objects.create(
        deck=deck,
        note_type=deck.note_type,
        guid="removida",
        field_values={},
        mod=now,
        deleted_at=now,
    )

    response = auth_client.get(f"/api/v1/decks/{deck.id}/sync/full/")

    assert response.status_code == 200
    body = response.json()
    assert body["deck_name"] == "Deck Completo"
    # full não inclui removidas — é o estado íntegro para reconstruir o deck
    assert [n["guid"] for n in body["notes"]] == ["viva"]
    assert body["note_types"][0]["field_names"] == ["Frente", "Verso"]
    assert body["subdecks"] == ["Capítulo 1"]


def test_full_requires_subscription(auth_client, make_deck):
    deck = make_deck()

    assert auth_client.get(f"/api/v1/decks/{deck.id}/sync/full/").status_code == 403
