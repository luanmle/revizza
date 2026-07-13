"""Contract tests: account deletion grace period and JSON export (FR-046, FR-047)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts import jobs
from apps.accounts.models import User
from apps.discussions.models import Comment

pytestmark = pytest.mark.django_db

DELETION_URL = "/api/v1/accounts/me/deletion-request/"
EXPORT_URL = "/api/v1/accounts/me/export/"


def test_schedule_and_cancel_account_deletion(auth_client, user):
    scheduled = auth_client.post(DELETION_URL)

    assert scheduled.status_code == 202
    user.refresh_from_db()
    assert user.deletion_requested_at is not None
    assert scheduled.json()["scheduled_for"] == (
        user.deletion_requested_at + timedelta(days=7)
    ).isoformat().replace("+00:00", "Z")

    cancelled = auth_client.delete(DELETION_URL)

    assert cancelled.status_code == 204
    user.refresh_from_db()
    assert user.deletion_requested_at is None


def test_cannot_cancel_after_grace_period(auth_client, user):
    user.deletion_requested_at = timezone.now() - timedelta(days=8)
    user.save(update_fields=["deletion_requested_at"])

    response = auth_client.delete(DELETION_URL)

    assert response.status_code == 409


def test_grace_job_deletes_user_but_anonymizes_community_content(
    user, make_note, make_suggestion, subscribe, monkeypatch
):
    note = make_note()
    subscribe(note.deck)
    suggestion = make_suggestion(notes=[note], author=user)
    comment = Comment.objects.create(author=user, note=note, body="Contexto útil")
    user.deletion_requested_at = timezone.now() - timedelta(days=8)
    user.save(update_fields=["deletion_requested_at"])
    deleted_auth_ids = []
    monkeypatch.setattr(
        "apps.accounts.supabase_gateway.delete_user",
        lambda auth_id: deleted_auth_ids.append(str(auth_id)),
    )

    deleted = jobs.delete_expired_accounts()

    assert deleted == 1
    assert deleted_auth_ids == [str(user.auth_id)]
    assert not User.objects.filter(pk=user.pk).exists()
    suggestion.refresh_from_db()
    comment.refresh_from_db()
    assert suggestion.author is None
    assert comment.author is None
    assert not note.deck.subscriptions.exists()


def test_export_contains_only_requesting_users_personal_content(
    auth_client, user, make_note, make_suggestion, make_user
):
    note = make_note()
    suggestion = make_suggestion(notes=[note], author=user)
    own_comment = Comment.objects.create(author=user, note=note, body="Meu comentário")
    other = make_user("outra@example.com")
    Comment.objects.create(author=other, note=note, body="Comentário alheio")

    response = auth_client.get(EXPORT_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["email"] == user.email
    assert [item["id"] for item in body["suggestions"]] == [str(suggestion.id)]
    assert [item["id"] for item in body["comments"]] == [str(own_comment.id)]
    assert body["comments"][0]["body"] == "Meu comentário"
