"""Contract test: POST /api/v1/notes/{id}/suggestions/change/ (contracts/suggestions.md, FR-013 a FR-016)."""

import uuid

import pytest

from apps.suggestions.models import Suggestion

pytestmark = pytest.mark.django_db


def _url(note):
    return f"/api/v1/notes/{note.id}/suggestions/change/"


PAYLOAD = {
    "change_category": "erro_conteudo",
    "justification": "O gabarito oficial diz outra coisa.",
    "proposed_field_values": {"Verso": "Resposta <b>corrigida</b>"},
}


def test_create_change_suggestion_pending_linked_to_note(
    auth_client, user, make_note, subscribe
):
    note = make_note()
    subscribe(note.deck)

    response = auth_client.post(_url(note), PAYLOAD, format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "change"
    assert body["status"] == "pending"
    assert body["change_category"] == "erro_conteudo"
    assert body["justification"] == PAYLOAD["justification"]
    assert body["note_ids"] == [str(note.id)]
    suggestion = Suggestion.objects.get(pk=body["id"])
    assert suggestion.author == user
    assert suggestion.deck == note.deck
    assert list(suggestion.target_notes.values_list("note_id", flat=True)) == [note.id]


def test_justification_is_required(auth_client, make_note, subscribe):
    note = make_note()
    subscribe(note.deck)
    payload = {**PAYLOAD, "justification": ""}

    response = auth_client.post(_url(note), payload, format="json")

    assert response.status_code == 400


def test_change_category_is_required(auth_client, make_note, subscribe):
    note = make_note()
    subscribe(note.deck)
    payload = {k: v for k, v in PAYLOAD.items() if k != "change_category"}

    response = auth_client.post(_url(note), payload, format="json")

    assert response.status_code == 400


def test_proposed_html_is_sanitized_server_side(auth_client, make_note, subscribe):
    """FR-015: scripts e handlers inline nunca persistem."""
    note = make_note()
    subscribe(note.deck)
    payload = {
        **PAYLOAD,
        "proposed_field_values": {
            "Verso": '<b>ok</b><script>alert(1)</script><img src="x" onerror="alert(1)">'
        },
    }

    response = auth_client.post(_url(note), payload, format="json")

    assert response.status_code == 201
    stored = Suggestion.objects.get(pk=response.json()["id"]).proposed_field_values
    assert "<script" not in stored["Verso"]
    assert "onerror" not in stored["Verso"]
    assert "<b>ok</b>" in stored["Verso"]


def test_requires_subscription(auth_client, make_note):
    note = make_note()

    response = auth_client.post(_url(note), PAYLOAD, format="json")

    assert response.status_code == 403


def test_unknown_note_returns_404(auth_client, db):
    response = auth_client.post(
        f"/api/v1/notes/{uuid.uuid4()}/suggestions/change/", PAYLOAD, format="json"
    )

    assert response.status_code == 404


def test_requires_authentication(api_client, make_note):
    note = make_note()

    response = api_client.post(_url(note), PAYLOAD, format="json")

    assert response.status_code == 401


# --- Validação semântica no servidor (FR-020, US4/AC4 — T134) ---


def test_suggestion_without_fields_or_tags_is_rejected(
    auth_client, make_note, subscribe
):
    note = make_note()
    subscribe(note.deck)
    payload = {k: v for k, v in PAYLOAD.items() if k != "proposed_field_values"}

    response = auth_client.post(_url(note), payload, format="json")

    assert response.status_code == 400
    assert Suggestion.objects.count() == 0


def test_unknown_field_is_rejected(auth_client, make_note, subscribe):
    note = make_note()
    subscribe(note.deck)
    payload = {**PAYLOAD, "proposed_field_values": {"Inexistente": "x"}}

    response = auth_client.post(_url(note), payload, format="json")

    assert response.status_code == 400
    assert Suggestion.objects.count() == 0


def test_noop_suggestion_is_rejected(auth_client, make_note, subscribe):
    """Proposta idêntica ao conteúdo atual não cria sugestão."""
    note = make_note()
    subscribe(note.deck)
    payload = {
        **PAYLOAD,
        "proposed_field_values": dict(note.field_values),
    }

    response = auth_client.post(_url(note), payload, format="json")

    assert response.status_code == 400
    assert Suggestion.objects.count() == 0


# --- Tags propostas (FR-013 Nova tag/Tag atualizada — T125) ---


def test_tags_only_suggestion_is_persisted(auth_client, make_note, subscribe):
    note = make_note()
    subscribe(note.deck)
    payload = {
        "change_category": "nova_tag",
        "justification": "Padronizar a tag da matéria.",
        "tags": [" lei-14133 ", "lei-14133", "licitação"],
    }

    response = auth_client.post(_url(note), payload, format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["tags"] == ["lei-14133", "licitação"]  # trim + dedupe
    suggestion = Suggestion.objects.get(pk=body["id"])
    assert suggestion.proposed_tags == ["lei-14133", "licitação"]


def test_blank_tag_is_rejected(auth_client, make_note, subscribe):
    note = make_note()
    subscribe(note.deck)
    payload = {**PAYLOAD, "tags": ["ok", "  "]}

    response = auth_client.post(_url(note), payload, format="json")

    assert response.status_code == 400


def test_noop_tag_suggestion_is_rejected(auth_client, make_note, subscribe):
    note = make_note(tags=["lei-14133"])
    subscribe(note.deck)
    payload = {
        "change_category": "nova_tag",
        "justification": "Tag já presente.",
        "tags": ["lei-14133"],
    }

    response = auth_client.post(_url(note), payload, format="json")

    assert response.status_code == 400
