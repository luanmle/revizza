"""Contract test: GET /api/v1/notes/resolve/?guid= (contracts/note-resolve.md §3, US2)."""

import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db

BASE = settings.FRONTEND_BASE_URL


def test_resolve_returns_ids_and_urls(auth_client, make_note):
    note = make_note()

    response = auth_client.get(f"/api/v1/notes/resolve/?guid={note.guid}")

    assert response.status_code == 200
    body = response.json()
    assert body["note_id"] == str(note.id)
    assert body["deck_id"] == str(note.deck_id)
    assert body["web_url"] == f"{BASE}/decks/{note.deck_id}/notes/{note.id}"
    assert (
        body["history_url"]
        == f"{BASE}/decks/{note.deck_id}/suggestions?note_id={note.id}"
    )


def test_missing_guid_is_400(auth_client):
    response = auth_client.get("/api/v1/notes/resolve/")

    assert response.status_code == 400
    assert "guid" in response.json()


def test_unknown_guid_is_404(auth_client):
    response = auth_client.get("/api/v1/notes/resolve/?guid=nao-existe")

    assert response.status_code == 404


def test_resolve_requires_auth(api_client, make_note):
    note = make_note()

    response = api_client.get(f"/api/v1/notes/resolve/?guid={note.guid}")

    assert response.status_code == 401
