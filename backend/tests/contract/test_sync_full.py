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


def test_full_sync_sets_last_synced_at(auth_client, user, make_deck, note_type):
    deck = make_deck(name="Deck Full")
    Subscription.objects.create(user=user, deck=deck)

    assert auth_client.get(f"/api/v1/decks/{deck.id}/sync/full/").status_code == 200

    sub = Subscription.objects.get(user=user, deck=deck)
    assert sub.last_synced_at is not None


def test_last_synced_at_write_does_not_alter_sync_payload(
    auth_client, user, make_deck, note_type
):
    """Principle VIII: gravar last_synced_at não altera o payload de sync."""
    deck = make_deck(name="Deck Full")
    Subscription.objects.create(user=user, deck=deck)
    Note.objects.create(
        deck=deck, note_type=note_type, guid="a",
        field_values={"Frente": "Q", "Verso": "A"}, mod=timezone.now(),
    )

    before = auth_client.get(f"/api/v1/decks/{deck.id}/sync/full/").json()

    auth_client.credentials(HTTP_X_SYNC_RUN_ID="run-1")
    after = auth_client.get(f"/api/v1/decks/{deck.id}/sync/full/").json()

    assert before == after


def test_full_deck_name_decoupled_from_editable_name(auth_client, user, make_deck):
    """research.md Decisão 4 / FR-006: deck_name do payload vem de anki_deck_name,
    imune a edições futuras de Deck.name — provado antes mesmo do endpoint de edição existir."""
    deck = make_deck(name="Nome Original")
    Subscription.objects.create(user=user, deck=deck)
    assert deck.anki_deck_name == "Nome Original"

    deck.name = "Nome Editado"
    deck.save(update_fields=["name"])

    body = auth_client.get(f"/api/v1/decks/{deck.id}/sync/full/").json()
    assert body["deck_name"] == "Nome Original"
