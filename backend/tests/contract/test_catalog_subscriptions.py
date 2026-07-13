"""Contract test: subscribe/unsubscribe/preferences (contracts/catalog.md, FR-009)."""

import pytest

pytestmark = pytest.mark.django_db


def _url(deck, suffix=""):
    return f"/api/v1/decks/{deck.id}/subscriptions/{suffix}"


def test_subscribe_creates_link_and_increments_counter(auth_client, user, make_deck):
    deck = make_deck()

    response = auth_client.post(_url(deck), format="json")

    assert response.status_code == 201
    body = response.json()
    assert body["sync_trigger_manual"] is True  # default do data-model
    assert body["delete_notes_on_removal"] is False
    deck.refresh_from_db()
    assert deck.subscriber_count == 1
    assert deck.subscriptions.filter(user=user).exists()


def test_subscribe_is_idempotent(auth_client, make_deck):
    deck = make_deck()
    auth_client.post(_url(deck), format="json")

    response = auth_client.post(_url(deck), format="json")

    assert response.status_code == 200
    deck.refresh_from_db()
    assert deck.subscriber_count == 1


def test_subscribe_accepts_sync_preferences(auth_client, make_deck):
    deck = make_deck()

    response = auth_client.post(
        _url(deck), {"sync_trigger_on_anki_open": True}, format="json"
    )

    assert response.status_code == 201
    assert response.json()["sync_trigger_on_anki_open"] is True


def test_patch_updates_preferences(auth_client, make_deck):
    deck = make_deck()
    auth_client.post(_url(deck), format="json")

    response = auth_client.patch(
        _url(deck, "me/"), {"delete_notes_on_removal": True}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["delete_notes_on_removal"] is True


def test_unsubscribe_removes_link_and_decrements_counter(auth_client, make_deck):
    deck = make_deck()
    auth_client.post(_url(deck), format="json")

    response = auth_client.delete(_url(deck, "me/"))

    assert response.status_code == 204
    deck.refresh_from_db()
    assert deck.subscriber_count == 0
    assert not deck.subscriptions.exists()


def test_preferences_require_existing_subscription(auth_client, make_deck):
    deck = make_deck()

    assert auth_client.patch(_url(deck, "me/"), {}, format="json").status_code == 404
    assert auth_client.delete(_url(deck, "me/")).status_code == 404
