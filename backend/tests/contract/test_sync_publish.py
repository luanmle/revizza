"""Contract test: POST /decks/{id}/publish/ (contracts/sync.md, T035)."""

import uuid

import pytest

from apps.catalog.models import Deck

pytestmark = pytest.mark.django_db


def _payload(**overrides):
    payload = {
        "name": "Direito Penal",
        "subject_tags": ["Direito"],
        "note_type": {
            "name": "Básico",
            "field_names": ["Frente", "Verso"],
            "templates": [
                {"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"}
            ],
            "css": ".card { }",
        },
        "notes": [
            {
                "guid": "n1",
                "field_values": {
                    "Frente": "<b>Q</b><script>x()</script>",
                    "Verso": "A",
                },
                "tags": ["penal"],
                "anki_deck_path": "Parte Geral",
            }
        ],
        "media": [{"filename": "figura.png", "content_hash": "a" * 64}],
    }
    payload.update(overrides)
    return payload


@pytest.fixture(autouse=True)
def mock_upload_url(monkeypatch):
    monkeypatch.setattr(
        "apps.sync.views.media.signed_upload_url",
        lambda path: f"https://storage.example/upload/{path}",
    )


def test_publish_creates_deck_notes_and_moderator(auth_client, user):
    deck_id = uuid.uuid4()

    response = auth_client.post(
        f"/api/v1/decks/{deck_id}/publish/", _payload(), format="json"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["note_count"] == 1
    assert "a" * 64 in body["media_upload_urls"]  # hash inédito → URL de upload
    deck = Deck.objects.get(pk=deck_id)
    assert deck.moderators.filter(user=user, status="active").exists()
    note = deck.notes.get()
    assert "<script>" not in note.field_values["Frente"]  # FR-015 no publish
    assert note.anki_deck_path == "Parte Geral"


def test_republish_is_rejected_and_keeps_web_content_authoritative(auth_client):
    deck_id = uuid.uuid4()
    url = f"/api/v1/decks/{deck_id}/publish/"
    auth_client.post(url, _payload(), format="json")

    changed = _payload()
    changed["name"] = "Tentativa de sobrescrita local"
    changed["note_type"]["templates"].append(
        {"name": "Card 2", "qfmt": "{{Verso}}", "afmt": "{{Frente}}"}
    )
    response = auth_client.post(url, changed, format="json")

    assert response.status_code == 409
    deck = Deck.objects.get(pk=deck_id)
    assert deck.name == "Direito Penal"
    assert len(deck.note_type.templates) == 1
