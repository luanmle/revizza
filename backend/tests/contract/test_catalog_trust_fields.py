from datetime import timedelta

import pytest
from django.utils import timezone

from apps.catalog.models import DeckModerator

pytestmark = pytest.mark.django_db

URL = "/api/v1/decks/"


def test_list_exposes_creator_official_and_latest_content_update(
    auth_client, user, make_deck, make_note
):
    user.name = "Ana Silva"
    user.save(update_fields=["name"])
    deck = make_deck(creator=user, is_official=True)
    older = timezone.now() - timedelta(days=2)
    latest = timezone.now() - timedelta(hours=1)
    make_note(deck=deck, mod=older)
    make_note(deck=deck, mod=latest, deleted_at=latest)

    item = auth_client.get(URL).json()["results"][0]

    assert item["creator"] == {
        "id": str(user.id),
        "name": "Ana Silva",
        "avatar_url": None,
    }
    assert item["is_official"] is True
    assert item["last_updated_at"] == latest.isoformat().replace("+00:00", "Z")


def test_deck_without_notes_uses_created_at_and_creator_can_be_null(
    auth_client, make_deck
):
    deck = make_deck()

    item = auth_client.get(URL).json()["results"][0]

    assert item["creator"] is None
    assert item["last_updated_at"] == deck.created_at.isoformat().replace("+00:00", "Z")


def test_detail_lists_only_active_moderators_without_email(
    auth_client, user, make_user, make_deck, make_moderator
):
    creator = make_user("criador@example.com")
    creator.name = "Criador"
    creator.save(update_fields=["name"])
    active = make_user("ativo@example.com")
    active.name = "Moderador"
    active.save(update_fields=["name"])
    pending = make_user("pendente@example.com")
    deck = make_deck(creator=creator)
    make_moderator(deck, user)
    relation = make_moderator(deck, active)
    make_moderator(deck, pending, DeckModerator.Status.PENDING)

    body = auth_client.get(f"{URL}{deck.id}/").json()

    assert body["creator"]["name"] == "Criador"
    assert {item["user_id"] for item in body["moderators"]} == {
        str(user.id),
        str(active.id),
    }
    assert str(relation.id) in {item["id"] for item in body["moderators"]}
    assert "email" not in str(body["moderators"])
    assert pending.email not in str(body)


def test_creator_persists_after_moderator_relation_is_removed(
    auth_client, user, make_deck, make_moderator
):
    deck = make_deck(creator=user)
    make_moderator(deck, user).delete()

    assert auth_client.get(f"{URL}{deck.id}/").json()["creator"]["id"] == str(user.id)


def test_moderator_patch_cannot_mark_deck_official(
    auth_client, user, make_deck, make_moderator
):
    deck = make_deck(is_official=False)
    make_moderator(deck, user)

    response = auth_client.patch(
        f"{URL}{deck.id}/", {"name": "Editado", "is_official": True}, format="json"
    )

    assert response.status_code == 200
    deck.refresh_from_db()
    assert deck.name == "Editado"
    assert deck.is_official is False
