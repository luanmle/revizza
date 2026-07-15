"""Contract test: POST /decks/{id}/publish/ (contracts/sync.md, T035)."""

import uuid

import pytest
from django.test import override_settings
from django.core.cache import cache

from apps.catalog.models import Deck

pytestmark = pytest.mark.django_db


def _payload(**overrides):
    payload = {
        "name": "Direito Penal",
        "subject_tags": ["Direito"],
        "note_types": [
            {
                "name": "Básico",
                "field_names": ["Frente", "Verso"],
                "templates": [
                    {"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"}
                ],
                "css": ".card { }",
            }
        ],
        "notes": [
            {
                "guid": "n1",
                "field_values": {
                    "Frente": "<b>Q</b><script>x()</script>",
                    "Verso": "A",
                },
                "tags": ["penal"],
                "anki_deck_path": "Parte Geral",
                "note_type_index": 0,
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


def test_publish_sanitizes_deck_description(auth_client):
    deck_id = uuid.uuid4()

    response = auth_client.post(
        f"/api/v1/decks/{deck_id}/publish/",
        _payload(
            description=(
                '<p><strong>Texto</strong><img src="https://example.com/x.png" '
                'onerror="alert(1)"><script>alert(1)</script></p>'
            )
        ),
        format="json",
    )

    assert response.status_code == 201
    description = Deck.objects.get(pk=deck_id).description
    assert "<strong>Texto</strong>" in description
    assert "onerror" not in description
    assert "<script>" not in description


def test_republish_is_rejected_and_keeps_web_content_authoritative(auth_client):
    deck_id = uuid.uuid4()
    url = f"/api/v1/decks/{deck_id}/publish/"
    auth_client.post(url, _payload(), format="json")

    changed = _payload()
    changed["name"] = "Tentativa de sobrescrita local"
    changed["note_types"][0]["templates"].append(
        {"name": "Card 2", "qfmt": "{{Verso}}", "afmt": "{{Frente}}"}
    )
    response = auth_client.post(url, changed, format="json")

    assert response.status_code == 409
    deck = Deck.objects.get(pk=deck_id)
    assert deck.name == "Direito Penal"
    assert len(deck.notes.get().note_type.templates) == 1


def _multi_type_payload():
    return _payload(
        note_types=[
            {
                "name": "Básico",
                "field_names": ["Frente", "Verso"],
                "templates": [
                    {"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"}
                ],
                "css": "",
            },
            {
                "name": "Cloze",
                "field_names": ["Texto"],
                "templates": [
                    {"name": "Cloze", "qfmt": "{{Texto}}", "afmt": "{{Texto}}"}
                ],
                "css": "",
            },
        ],
        notes=[
            {"guid": "n1", "field_values": {"Frente": "Q", "Verso": "A"},
             "tags": [], "anki_deck_path": "", "note_type_index": 0},
            {"guid": "n2", "field_values": {"Texto": "{{c1::x}}"},
             "tags": [], "anki_deck_path": "", "note_type_index": 1},
        ],
        media=[],
    )


def test_publish_creates_one_note_type_per_item_and_associates_by_index(auth_client):
    deck_id = uuid.uuid4()

    response = auth_client.post(
        f"/api/v1/decks/{deck_id}/publish/", _multi_type_payload(), format="json"
    )

    assert response.status_code == 201
    deck = Deck.objects.get(pk=deck_id)
    assert deck.notes.count() == 2
    by_guid = {n.guid: n.note_type.name for n in deck.notes.all()}
    assert by_guid == {"n1": "Básico", "n2": "Cloze"}


def test_publish_rejects_note_type_index_out_of_range(auth_client):
    deck_id = uuid.uuid4()
    payload = _multi_type_payload()
    payload["notes"][1]["note_type_index"] = 5

    response = auth_client.post(
        f"/api/v1/decks/{deck_id}/publish/", payload, format="json"
    )

    assert response.status_code == 400
    assert not Deck.objects.filter(pk=deck_id).exists()  # atômico: nada persiste


def test_publish_rejects_malformed_note_type_atomically(auth_client):
    """FR-004: item sem field_names no meio da lista → 400, nada persiste."""
    from apps.notes.models import NoteType

    deck_id = uuid.uuid4()
    payload = _multi_type_payload()
    del payload["note_types"][1]["field_names"]
    before = NoteType.objects.count()

    response = auth_client.post(
        f"/api/v1/decks/{deck_id}/publish/", payload, format="json"
    )

    assert response.status_code == 400
    assert not Deck.objects.filter(pk=deck_id).exists()
    assert NoteType.objects.count() == before  # nenhum NoteType criado


# Constituição Princípio VIII: campos de agendamento/estado de cartão que os models de
# sync (Note/NoteType) e os payloads de sync/publish nunca podem tocar
_CARD_STATE_FIELDS = {
    "ease",
    "interval",
    "due",
    "reps",
    "lapses",
    "queue",
    "ivl",
    "factor",
    "review_history",
    "reviews",
}


def test_sync_models_hold_no_card_state_fields():
    """Princípio VIII: Note/NoteType são Conteúdo da Nota, nunca Estado do Cartão."""
    from apps.notes.models import Note, NoteType

    for model in (Note, NoteType):
        names = {f.name for f in model._meta.get_fields()}
        leaked = names & _CARD_STATE_FIELDS
        assert not leaked, f"{model.__name__} vazou estado de cartão: {leaked}"


def test_sync_payloads_expose_no_card_state(auth_client, user):
    """Princípio VIII: delta/full/publish só emitem Conteúdo da Nota."""
    from apps.catalog.models import Subscription

    deck_id = uuid.uuid4()
    auth_client.post(f"/api/v1/decks/{deck_id}/publish/", _payload(), format="json")
    Subscription.objects.create(user=user, deck=Deck.objects.get(pk=deck_id))

    # mesmo run-id: full+delta contam como uma execução, sem bater no limite de 10s
    auth_client.credentials(HTTP_X_SYNC_RUN_ID="run-vp")
    for path in (f"/decks/{deck_id}/sync/full/", f"/decks/{deck_id}/sync/delta/"):
        body = auth_client.get(f"/api/v1{path}").json()
        note_keys = {k for note in body["notes"] for k in note}
        assert not (note_keys & _CARD_STATE_FIELDS), f"{path} vazou estado de cartão"


@override_settings(RATELIMIT_PUBLISH_RATE="1/h")
def test_publish_is_rate_limited_per_user(auth_client, mock_upload_url):
    cache.clear()
    first = auth_client.post(
        f"/api/v1/decks/{uuid.uuid4()}/publish/", _payload(), format="json"
    )
    blocked = auth_client.post(
        f"/api/v1/decks/{uuid.uuid4()}/publish/", _payload(), format="json"
    )

    assert first.status_code == 201
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "3600"
