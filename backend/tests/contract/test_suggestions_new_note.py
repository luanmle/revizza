"""Contract tests: new-note suggestions (contracts/suggestions.md, FR-018)."""

import pytest

from apps.notes.models import Note
from apps.suggestions.models import Suggestion

pytestmark = pytest.mark.django_db


@pytest.fixture
def deck(make_note, subscribe):
    # nota dá ao deck exatamente um tipo, resolvido automaticamente na sugestão (T010)
    deck = make_note(guid="__seed__").deck
    subscribe(deck)
    return deck


def _url(deck):
    return f"/api/v1/decks/{deck.id}/suggestions/new-note/"


PAYLOAD = {
    "justification": "Este conceito ainda não existe no deck.",
    "proposed_field_values": {
        "Frente": "Questão <b>nova</b>",
        "Verso": "",
    },
    "tags": ["Direito", "Revisar"],
}


def test_create_new_note_suggestion_flags_empty_fields(auth_client, user, deck):
    response = auth_client.post(_url(deck), PAYLOAD, format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "new_note"
    assert body["status"] == "pending"
    assert body["note_ids"] == []
    assert body["tags"] == ["Direito", "Revisar"]
    assert body["empty_fields"] == ["Verso"]
    suggestion = Suggestion.objects.get(pk=body["id"])
    assert suggestion.author == user
    assert suggestion.deck == deck
    assert suggestion.proposed_tags == ["Direito", "Revisar"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("justification", ""), ("tags", [])],
)
def test_justification_and_tags_are_required(auth_client, deck, field, value):
    response = auth_client.post(_url(deck), {**PAYLOAD, field: value}, format="json")

    assert response.status_code == 400


def test_requires_exact_note_type_fields(auth_client, deck):
    missing = auth_client.post(
        _url(deck),
        {**PAYLOAD, "proposed_field_values": {"Frente": "Só um campo"}},
        format="json",
    )
    unknown = auth_client.post(
        _url(deck),
        {
            **PAYLOAD,
            "proposed_field_values": {
                **PAYLOAD["proposed_field_values"],
                "Inexistente": "valor",
            },
        },
        format="json",
    )

    assert missing.status_code == 400
    assert unknown.status_code == 400


def test_new_note_html_is_sanitized(auth_client, deck):
    response = auth_client.post(
        _url(deck),
        {
            **PAYLOAD,
            "proposed_field_values": {
                "Frente": "<b>ok</b><script>alert(1)</script>",
                "Verso": "Resposta",
            },
        },
        format="json",
    )

    assert response.status_code == 201
    stored = Suggestion.objects.get(pk=response.json()["id"])
    assert stored.proposed_field_values["Frente"] == "<b>ok</b>"


def test_new_note_suggestion_requires_subscription(auth_client, make_deck):
    response = auth_client.post(_url(make_deck()), PAYLOAD, format="json")

    assert response.status_code == 403


def test_accepting_new_note_creates_official_note(
    auth_client, deck, user, make_user, make_moderator
):
    created = auth_client.post(_url(deck), PAYLOAD, format="json")
    moderator = make_user("moderadora@example.com")
    make_moderator(deck, moderator)
    auth_client.force_authenticate(user=moderator)

    accepted = auth_client.post(f"/api/v1/suggestions/{created.json()['id']}/accept/")

    assert accepted.status_code == 200
    note = Note.objects.exclude(guid="__seed__").get(deck=deck)
    assert note.field_values == PAYLOAD["proposed_field_values"]
    assert note.tags == PAYLOAD["tags"]
    deck.refresh_from_db()
    assert deck.note_count == 1
