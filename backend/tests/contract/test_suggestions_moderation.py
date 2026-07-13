"""Contract test: votos, comentários e accept/reject de sugestão
(contracts/suggestions.md, FR-023 a FR-027)."""

import pytest
from rest_framework.test import APIClient

from apps.suggestions.models import Suggestion, SuggestionVote

pytestmark = pytest.mark.django_db


@pytest.fixture
def deck(make_deck, subscribe):
    deck = make_deck()
    subscribe(deck)
    return deck


@pytest.fixture
def suggestion(deck, make_note, make_suggestion):
    return make_suggestion(
        notes=[make_note(deck=deck)],
        proposed_field_values={"Verso": "Resposta corrigida"},
    )


@pytest.fixture
def moderator(make_user):
    return make_user("moderadora@example.com")


@pytest.fixture
def mod_client(moderator, deck, make_moderator):
    make_moderator(deck, moderator)
    client = APIClient()
    client.force_authenticate(user=moderator)
    return client


def _votes_url(suggestion):
    return f"/api/v1/suggestions/{suggestion.id}/votes/"


def _comments_url(suggestion):
    return f"/api/v1/suggestions/{suggestion.id}/comments/"


# --- Votos (FR-023) ---


def test_vote_like_creates_vote(auth_client, user, suggestion):
    response = auth_client.post(
        _votes_url(suggestion), {"value": "like"}, format="json"
    )

    assert response.status_code == 201
    vote = SuggestionVote.objects.get(suggestion=suggestion, user=user)
    assert vote.value == "like"


def test_vote_is_upsert_per_user(auth_client, user, suggestion):
    auth_client.post(_votes_url(suggestion), {"value": "like"}, format="json")

    response = auth_client.post(
        _votes_url(suggestion), {"value": "dislike"}, format="json"
    )

    assert response.status_code in (200, 201)
    assert SuggestionVote.objects.filter(suggestion=suggestion).count() == 1
    assert (
        SuggestionVote.objects.get(suggestion=suggestion, user=user).value
        == "dislike"
    )


def test_invalid_vote_value_is_rejected(auth_client, suggestion):
    response = auth_client.post(
        _votes_url(suggestion), {"value": "love"}, format="json"
    )

    assert response.status_code == 400


def test_delete_own_vote(auth_client, suggestion):
    auth_client.post(_votes_url(suggestion), {"value": "like"}, format="json")

    response = auth_client.delete(f"{_votes_url(suggestion)}me/")

    assert response.status_code == 204
    assert SuggestionVote.objects.count() == 0


def test_vote_requires_subscription(suggestion, make_user):
    outsider = APIClient()
    outsider.force_authenticate(user=make_user("fora@example.com"))

    response = outsider.post(
        _votes_url(suggestion), {"value": "like"}, format="json"
    )

    assert response.status_code == 403


# --- Thread da sugestão (FR-024) ---


def test_post_and_list_suggestion_comments(auth_client, user, suggestion):
    created = auth_client.post(
        _comments_url(suggestion), {"body": "Concordo com a correção."}, format="json"
    )

    assert created.status_code == 201

    listed = auth_client.get(_comments_url(suggestion))

    assert listed.status_code == 200
    results = listed.json()["results"]
    assert len(results) == 1
    assert results[0]["body"] == "Concordo com a correção."
    assert results[0]["author"] == str(user.id)


def test_empty_comment_body_is_rejected(auth_client, suggestion):
    response = auth_client.post(_comments_url(suggestion), {"body": ""}, format="json")

    assert response.status_code == 400


def test_comments_require_subscription(suggestion, make_user):
    outsider = APIClient()
    outsider.force_authenticate(user=make_user("fora@example.com"))

    response = outsider.get(_comments_url(suggestion))

    assert response.status_code == 403


# --- Accept (FR-025, FR-026) ---


def test_moderator_accepts_change_and_official_note_is_updated(
    mod_client, moderator, suggestion
):
    note = suggestion.target_notes.get().note
    mod_before = note.mod

    response = mod_client.post(f"/api/v1/suggestions/{suggestion.id}/accept/")

    assert response.status_code == 200
    suggestion.refresh_from_db()
    assert suggestion.status == "accepted"
    assert suggestion.decided_by == moderator
    note.refresh_from_db()
    # campo proposto sobrescreve; demais campos intactos
    assert note.field_values["Verso"] == "Resposta corrigida"
    assert note.field_values["Frente"] == "Pergunta"
    # nota entra na fila de sync: `mod` avança (FR-026)
    assert note.mod > mod_before


def test_moderator_accepts_deletion_and_note_is_soft_deleted(
    mod_client, deck, make_note, make_suggestion
):
    note = make_note(deck=deck)
    suggestion = make_suggestion(notes=[note], type=Suggestion.Type.DELETION)

    response = mod_client.post(f"/api/v1/suggestions/{suggestion.id}/accept/")

    assert response.status_code == 200
    note.refresh_from_db()
    assert note.deleted_at is not None


def test_non_moderator_cannot_accept(auth_client, suggestion):
    response = auth_client.post(f"/api/v1/suggestions/{suggestion.id}/accept/")

    assert response.status_code == 403
    suggestion.refresh_from_db()
    assert suggestion.status == "pending"


def test_pending_invite_moderator_cannot_accept(
    deck, suggestion, make_user, make_moderator
):
    from apps.catalog.models import DeckModerator

    invited = make_user("convidada@example.com")
    make_moderator(deck, invited, status=DeckModerator.Status.PENDING)
    client = APIClient()
    client.force_authenticate(user=invited)

    response = client.post(f"/api/v1/suggestions/{suggestion.id}/accept/")

    assert response.status_code == 403


def test_accept_non_pending_returns_409(mod_client, suggestion):
    Suggestion.objects.filter(pk=suggestion.pk).update(
        status=Suggestion.Status.REJECTED
    )

    response = mod_client.post(f"/api/v1/suggestions/{suggestion.id}/accept/")

    assert response.status_code == 409


# --- Reject (FR-025, FR-027) ---


def test_moderator_rejects_with_reason(mod_client, moderator, suggestion):
    response = mod_client.post(
        f"/api/v1/suggestions/{suggestion.id}/reject/",
        {"rejection_reason": "Fonte desatualizada."},
        format="json",
    )

    assert response.status_code == 200
    suggestion.refresh_from_db()
    assert suggestion.status == "rejected"
    assert suggestion.rejection_reason == "Fonte desatualizada."
    assert suggestion.decided_by == moderator


def test_reject_reason_is_optional(mod_client, suggestion):
    response = mod_client.post(f"/api/v1/suggestions/{suggestion.id}/reject/")

    assert response.status_code == 200
    suggestion.refresh_from_db()
    assert suggestion.status == "rejected"


def test_reject_does_not_touch_official_note(mod_client, suggestion):
    note = suggestion.target_notes.get().note
    original = note.field_values

    mod_client.post(f"/api/v1/suggestions/{suggestion.id}/reject/")

    note.refresh_from_db()
    assert note.field_values == original


def test_reject_non_pending_returns_409(mod_client, suggestion):
    Suggestion.objects.filter(pk=suggestion.pk).update(
        status=Suggestion.Status.ACCEPTED
    )

    response = mod_client.post(f"/api/v1/suggestions/{suggestion.id}/reject/")

    assert response.status_code == 409


def test_non_moderator_cannot_reject(auth_client, suggestion):
    response = auth_client.post(f"/api/v1/suggestions/{suggestion.id}/reject/")

    assert response.status_code == 403
