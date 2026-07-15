"""Contract test: GET /api/v1/go/note/<guid>/ (contracts/note-resolve.md §1, US1)."""

import pytest
from django.conf import settings

pytestmark = pytest.mark.django_db

BASE = settings.FRONTEND_BASE_URL


def test_valid_guid_redirects_to_note_page(api_client, make_note):
    note = make_note()

    response = api_client.get(f"/api/v1/go/note/{note.guid}/")

    assert response.status_code == 302
    assert response["Location"] == f"{BASE}/decks/{note.deck_id}/notes/{note.id}"


def test_unknown_guid_redirects_to_friendly_page(api_client):
    response = api_client.get("/api/v1/go/note/nao-existe/")

    assert response.status_code == 302
    assert response["Location"] == f"{BASE}/nota-nao-encontrada"


def test_deleted_note_redirects_to_friendly_page(api_client, make_note):
    from django.utils import timezone

    note = make_note()
    note.deleted_at = timezone.now()
    note.save(update_fields=["deleted_at"])

    response = api_client.get(f"/api/v1/go/note/{note.guid}/")

    assert response.status_code == 302
    assert response["Location"] == f"{BASE}/nota-nao-encontrada"


def test_history_redirect_carries_note_id_query(api_client, make_note):
    """§2 (US3): GUID válido → 302 para a lista filtrada por nota."""
    note = make_note()

    response = api_client.get(f"/api/v1/go/note/{note.guid}/history/")

    assert response.status_code == 302
    assert (
        response["Location"]
        == f"{BASE}/decks/{note.deck_id}/suggestions?note_id={note.id}"
    )


def test_history_unknown_guid_redirects_to_friendly_page(api_client):
    response = api_client.get("/api/v1/go/note/nao-existe/history/")

    assert response.status_code == 302
    assert response["Location"] == f"{BASE}/nota-nao-encontrada"
