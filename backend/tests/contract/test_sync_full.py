"""Contract test: GET /decks/{id}/sync/full/ (contracts/sync.md, FR-035)."""

import pytest
from django.utils import timezone

from apps.catalog.models import Subscription
from apps.notes.models import Note, NoteType

pytestmark = pytest.mark.django_db


def test_full_returns_complete_live_deck(auth_client, user, make_deck, note_type):
    deck = make_deck(name="Deck Completo")
    Subscription.objects.create(user=user, deck=deck)
    now = timezone.now()
    Note.objects.create(
        deck=deck,
        note_type=note_type,
        guid="viva",
        field_values={"Frente": "Q", "Verso": "A"},
        anki_deck_path="Capítulo 1",
        mod=now,
    )
    Note.objects.create(
        deck=deck,
        note_type=note_type,
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


def test_full_returns_all_note_types_of_multi_type_deck(
    auth_client, user, make_deck, note_type
):
    """US2: deck com 2 tipos retorna os 2 note_types e cada nota com seu note_type_id."""
    deck = make_deck(name="Deck Misto")
    Subscription.objects.create(user=user, deck=deck)
    cloze = NoteType.objects.create(
        name="Cloze BR",
        field_names=["Texto", "Extra"],
        templates=[{"name": "Cloze"}],
    )
    now = timezone.now()
    Note.objects.create(
        deck=deck, note_type=note_type, guid="basica",
        field_values={"Frente": "Q", "Verso": "A"}, mod=now,
    )
    Note.objects.create(
        deck=deck, note_type=cloze, guid="cloze",
        field_values={"Texto": "{{c1::x}}"}, mod=now,
    )

    body = auth_client.get(f"/api/v1/decks/{deck.id}/sync/full/").json()

    nt_by_id = {nt["id"]: nt for nt in body["note_types"]}
    assert {nt["name"] for nt in body["note_types"]} == {"Básico", "Cloze BR"}
    by_guid = {n["guid"]: n for n in body["notes"]}
    assert nt_by_id[by_guid["basica"]["note_type_id"]]["name"] == "Básico"
    assert nt_by_id[by_guid["cloze"]["note_type_id"]]["name"] == "Cloze BR"


def test_full_requires_subscription(auth_client, make_deck):
    deck = make_deck()

    assert auth_client.get(f"/api/v1/decks/{deck.id}/sync/full/").status_code == 403
