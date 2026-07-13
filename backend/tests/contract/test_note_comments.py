"""Contract tests: note comment CRUD (contracts/notes.md, FR-012)."""

import pytest
from rest_framework.test import APIClient

from apps.discussions.models import Comment

pytestmark = pytest.mark.django_db


@pytest.fixture
def note(make_note, subscribe):
    note = make_note()
    subscribe(note.deck)
    return note


def _thread_url(note):
    return f"/api/v1/notes/{note.id}/comments/"


def test_author_can_create_list_edit_and_delete_note_comment(
    auth_client, user, note
):
    created = auth_client.post(
        _thread_url(note), {"body": "Comentário inicial."}, format="json"
    )

    assert created.status_code == 201
    comment_id = created.json()["id"]
    assert created.json()["author"] == str(user.id)

    listed = auth_client.get(_thread_url(note))
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()["results"]] == [comment_id]

    edited = auth_client.patch(
        f"/api/v1/comments/{comment_id}/",
        {"body": "Comentário corrigido."},
        format="json",
    )
    assert edited.status_code == 200
    assert edited.json()["body"] == "Comentário corrigido."
    assert edited.json()["edited_at"] is not None

    deleted = auth_client.delete(f"/api/v1/comments/{comment_id}/")
    assert deleted.status_code == 204
    assert not Comment.objects.filter(pk=comment_id).exists()


def test_note_thread_never_lists_suggestion_comments(
    auth_client, user, note, make_suggestion
):
    note_comment = Comment.objects.create(
        author=user, note=note, body="Thread geral."
    )
    suggestion = make_suggestion(notes=[note])
    Comment.objects.create(
        author=user, suggestion=suggestion, body="Thread da sugestão."
    )

    response = auth_client.get(_thread_url(note))

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["results"]] == [
        str(note_comment.id)
    ]


def test_non_author_cannot_edit_or_delete_comment(
    note, user, make_user
):
    comment = Comment.objects.create(author=user, note=note, body="Do autor.")
    outsider = APIClient()
    outsider.force_authenticate(user=make_user("outra@example.com"))

    edited = outsider.patch(
        f"/api/v1/comments/{comment.id}/", {"body": "Alterado."}, format="json"
    )
    deleted = outsider.delete(f"/api/v1/comments/{comment.id}/")

    assert edited.status_code == 403
    assert deleted.status_code == 403
    comment.refresh_from_db()
    assert comment.body == "Do autor."


def test_note_comments_require_subscription(make_note, make_user):
    note = make_note()
    outsider = APIClient()
    outsider.force_authenticate(user=make_user("fora@example.com"))

    response = outsider.get(_thread_url(note))

    assert response.status_code == 403
