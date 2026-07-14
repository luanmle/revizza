"""Contract test: POST /api/v1/suggestions/bulk-change/ (contracts/suggestions.md, FR-017)."""

import uuid

import pytest

from apps.suggestions.models import Suggestion

pytestmark = pytest.mark.django_db

URL = "/api/v1/suggestions/bulk-change/"


def _payload(notes):
    return {
        "note_ids": [str(n.id) for n in notes],
        "change_category": "nova_tag",
        "justification": "Padronizar a tag da matéria em todas as notas.",
        "proposed_field_values": {"Frente": "Pergunta <i>revisada</i>"},
    }


def test_bulk_creates_single_suggestion_covering_all_notes(
    auth_client, make_deck, make_note, subscribe
):
    deck = make_deck()
    subscribe(deck)
    notes = [make_note(deck=deck) for _ in range(3)]

    response = auth_client.post(URL, _payload(notes), format="json")

    assert response.status_code == 201
    body = response.json()
    assert sorted(body["note_ids"]) == sorted(str(n.id) for n in notes)
    assert Suggestion.objects.count() == 1  # uma única Suggestion (FR-017)
    suggestion = Suggestion.objects.get()
    assert suggestion.target_notes.count() == 3
    assert suggestion.status == "pending"


def test_empty_note_ids_is_rejected(auth_client, make_deck, subscribe):
    deck = make_deck()
    subscribe(deck)

    payload = {
        "note_ids": [],
        "change_category": "outro",
        "justification": "x",
    }
    response = auth_client.post(URL, payload, format="json")

    assert response.status_code == 400


def test_unknown_note_id_is_rejected(auth_client, make_deck, make_note, subscribe):
    deck = make_deck()
    subscribe(deck)
    note = make_note(deck=deck)

    payload = _payload([note])
    payload["note_ids"].append(str(uuid.uuid4()))
    response = auth_client.post(URL, payload, format="json")

    assert response.status_code == 400
    assert Suggestion.objects.count() == 0


def test_notes_from_different_decks_are_rejected(
    auth_client, make_deck, make_note, subscribe
):
    deck_a, deck_b = make_deck(), make_deck(name="Outro Deck")
    subscribe(deck_a)
    subscribe(deck_b)

    response = auth_client.post(
        URL, _payload([make_note(deck=deck_a), make_note(deck=deck_b)]), format="json"
    )

    assert response.status_code == 400
    assert Suggestion.objects.count() == 0


def test_requires_subscription_to_the_deck(auth_client, make_deck, make_note):
    deck = make_deck()

    response = auth_client.post(URL, _payload([make_note(deck=deck)]), format="json")

    assert response.status_code == 403
    assert Suggestion.objects.count() == 0


# --- Validação semântica em lote (FR-017/FR-020 — T134) ---


def test_bulk_noop_across_all_notes_is_rejected(
    auth_client, make_deck, make_note, subscribe
):
    deck = make_deck()
    subscribe(deck)
    notes = [make_note(deck=deck) for _ in range(2)]
    payload = {
        **_payload(notes),
        # proposta idêntica ao conteúdo atual de todas as notas (fixture padrão)
        "proposed_field_values": {"Frente": "Pergunta"},
    }

    response = auth_client.post(URL, payload, format="json")

    assert response.status_code == 400
    assert Suggestion.objects.count() == 0


def test_bulk_is_valid_when_at_least_one_note_differs(
    auth_client, make_deck, make_note, subscribe
):
    """Correção compartilhada válida: basta uma nota-alvo divergir (FR-017)."""
    deck = make_deck()
    subscribe(deck)
    same = make_note(deck=deck, field_values={"Frente": "Padronizada", "Verso": "A"})
    different = make_note(deck=deck)
    payload = {
        **_payload([same, different]),
        "proposed_field_values": {"Frente": "Padronizada"},
    }

    response = auth_client.post(URL, payload, format="json")

    assert response.status_code == 201


def test_bulk_tags_only_suggestion_is_persisted(
    auth_client, make_deck, make_note, subscribe
):
    """T125: a correção compartilhada pode ser só de tags (FR-013 Nova tag)."""
    deck = make_deck()
    subscribe(deck)
    notes = [make_note(deck=deck) for _ in range(2)]
    payload = {
        "note_ids": [str(n.id) for n in notes],
        "change_category": "nova_tag",
        "justification": "Padronizar a tag da matéria em todas as notas.",
        "tags": ["licitação"],
    }

    response = auth_client.post(URL, payload, format="json")

    assert response.status_code == 201
    suggestion = Suggestion.objects.get()
    assert suggestion.proposed_tags == ["licitação"]
    assert suggestion.target_notes.count() == 2
