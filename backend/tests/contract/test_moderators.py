"""Contract tests: moderator invite, accept, list and removal (FR-028 to FR-030)."""

import pytest
from rest_framework.test import APIClient

from apps.catalog.models import DeckModerator, Subscription

pytestmark = pytest.mark.django_db


@pytest.fixture
def deck(make_deck, user, make_moderator, subscribe):
    deck = make_deck()
    make_moderator(deck, user)
    subscribe(deck)
    return deck


def _list_url(deck):
    return f"/api/v1/decks/{deck.id}/moderators/"


def test_moderator_invites_and_invitee_accepts(
    auth_client, user, deck, make_user
):
    invited = make_user("convidada@example.com")
    Subscription.objects.create(user=invited, deck=deck)

    created = auth_client.post(
        _list_url(deck), {"email": invited.email}, format="json"
    )

    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    invite = DeckModerator.objects.get(pk=created.json()["id"])
    assert invite.user == invited
    assert invite.invited_by == user

    invitee_client = APIClient()
    invitee_client.force_authenticate(user=invited)
    accepted = invitee_client.post(
        f"/api/v1/deck-moderator-invites/{invite.id}/accept/"
    )

    assert accepted.status_code == 200
    invite.refresh_from_db()
    assert invite.status == DeckModerator.Status.ACTIVE


def test_subscriber_lists_active_and_pending_moderators(
    auth_client, deck, make_user, make_moderator
):
    pending = make_user("pendente@example.com")
    make_moderator(deck, pending, status=DeckModerator.Status.PENDING)

    response = auth_client.get(_list_url(deck))

    assert response.status_code == 200
    assert {item["status"] for item in response.json()["results"]} == {
        "active",
        "pending",
    }


def test_non_moderator_cannot_invite(deck, make_user):
    outsider = make_user("fora@example.com")
    candidate = make_user("candidata@example.com")
    Subscription.objects.create(user=outsider, deck=deck)
    client = APIClient()
    client.force_authenticate(user=outsider)

    response = client.post(
        _list_url(deck), {"email": candidate.email}, format="json"
    )

    assert response.status_code == 403


def test_moderator_can_remove_another_active_moderator(
    auth_client, deck, make_user, make_moderator
):
    other = make_user("outra-mod@example.com")
    make_moderator(deck, other)

    response = auth_client.delete(
        f"/api/v1/decks/{deck.id}/moderators/{other.id}/"
    )

    assert response.status_code == 204
    assert not DeckModerator.objects.filter(deck=deck, user=other).exists()


def test_cannot_remove_the_only_active_moderator(auth_client, user, deck):
    response = auth_client.delete(
        f"/api/v1/decks/{deck.id}/moderators/{user.id}/"
    )

    assert response.status_code == 409
    assert DeckModerator.objects.filter(
        deck=deck, user=user, status=DeckModerator.Status.ACTIVE
    ).exists()


def test_only_invited_user_can_accept(deck, make_user, make_moderator):
    invited = make_user("convidada@example.com")
    invite = make_moderator(deck, invited, status=DeckModerator.Status.PENDING)
    outsider = APIClient()
    outsider.force_authenticate(user=make_user("outra@example.com"))

    response = outsider.post(
        f"/api/v1/deck-moderator-invites/{invite.id}/accept/"
    )

    assert response.status_code == 403
