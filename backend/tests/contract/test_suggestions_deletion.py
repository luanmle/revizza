"""Contract tests: deletion suggestions (contracts/suggestions.md, FR-019)."""

import pytest

from apps.suggestions.models import Suggestion

pytestmark = pytest.mark.django_db


def _url(note):
    return f"/api/v1/notes/{note.id}/suggestions/deletion/"


def test_create_deletion_suggestion(auth_client, user, make_note, subscribe):
    note = make_note()
    subscribe(note.deck)

    response = auth_client.post(
        _url(note), {"justification": "Conteúdo duplicado."}, format="json"
    )

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "deletion"
    assert body["status"] == "pending"
    assert body["justification"] == "Conteúdo duplicado."
    assert body["note_ids"] == [str(note.id)]
    suggestion = Suggestion.objects.get(pk=body["id"])
    assert suggestion.author == user
    assert suggestion.target_notes.get().note == note


def test_deletion_justification_is_required(auth_client, make_note, subscribe):
    note = make_note()
    subscribe(note.deck)

    response = auth_client.post(_url(note), {"justification": ""}, format="json")

    assert response.status_code == 400


def test_deletion_suggestion_requires_subscription(auth_client, make_note):
    response = auth_client.post(
        _url(make_note()), {"justification": "Duplicada."}, format="json"
    )

    assert response.status_code == 403


def test_accepted_deletion_enters_sync_delta(
    auth_client, user, make_note, subscribe, make_user, make_moderator
):
    note = make_note()
    subscribe(note.deck)
    created = auth_client.post(_url(note), {"justification": "Remover."}, format="json")
    moderator = make_user("moderadora@example.com")
    make_moderator(note.deck, moderator)
    auth_client.force_authenticate(user=moderator)

    accepted = auth_client.post(f"/api/v1/suggestions/{created.json()['id']}/accept/")

    assert accepted.status_code == 200
    note.refresh_from_db()
    assert note.deleted_at is not None
    assert note.mod == note.deleted_at
