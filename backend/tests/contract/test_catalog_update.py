"""Contract test: PATCH /api/v1/decks/{id}/ (contracts/decks-update.md, FR-002/003/005/006/007/008)."""

import pytest

from apps.catalog.models import Deck, DeckModerator

pytestmark = pytest.mark.django_db


def _make_moderator(deck, user, status=DeckModerator.Status.ACTIVE):
    return DeckModerator.objects.create(deck=deck, user=user, status=status)


def test_active_moderator_updates_metadata(auth_client, user, make_deck):
    deck = make_deck(name="Nome Antigo", description="Antiga", subject_tags=["antigo"])
    _make_moderator(deck, user)

    response = auth_client.patch(
        f"/api/v1/decks/{deck.id}/",
        {"name": "Nome Novo", "description": "Nova", "subject_tags": ["novo"]},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Nome Novo"
    assert body["description"] == "Nova"
    assert body["subject_tags"] == ["novo"]

    for path in (f"/api/v1/decks/{deck.id}/", "/api/v1/decks/"):
        r = auth_client.get(path)
        data = r.json()
        item = data if "name" in data else next(
            d for d in data["results"] if d["id"] == str(deck.id)
        )
        assert item["name"] == "Nome Novo"


def test_partial_update_leaves_other_fields_unchanged(auth_client, user, make_deck):
    deck = make_deck(name="Fixo", description="Antiga", subject_tags=["fixo"])
    _make_moderator(deck, user)

    response = auth_client.patch(
        f"/api/v1/decks/{deck.id}/",
        {"description": "Só descrição"},
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "Só descrição"
    assert body["name"] == "Fixo"
    assert body["subject_tags"] == ["fixo"]


def test_blank_name_rejected(auth_client, user, make_deck):
    deck = make_deck(name="Original")
    _make_moderator(deck, user)

    response = auth_client.patch(
        f"/api/v1/decks/{deck.id}/",
        {"name": ""},
        content_type="application/json",
    )

    assert response.status_code == 400
    deck.refresh_from_db()
    assert deck.name == "Original"


def test_subject_tags_normalized(auth_client, user, make_deck):
    deck = make_deck(name="Deck")
    _make_moderator(deck, user)

    response = auth_client.patch(
        f"/api/v1/decks/{deck.id}/",
        {"subject_tags": ["a", "a", ""]},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["subject_tags"] == ["a"]


def test_subject_tags_non_list_rejected(auth_client, user, make_deck):
    deck = make_deck(name="Deck")
    _make_moderator(deck, user)

    response = auth_client.patch(
        f"/api/v1/decks/{deck.id}/",
        {"subject_tags": "not-a-list"},
        content_type="application/json",
    )

    assert response.status_code == 400


def test_description_sanitized(auth_client, user, make_deck):
    deck = make_deck(name="Deck")
    _make_moderator(deck, user)

    response = auth_client.patch(
        f"/api/v1/decks/{deck.id}/",
        {"description": '<script>alert(1)</script><p onerror="x">Texto</p>'},
        content_type="application/json",
    )

    assert response.status_code == 200
    description = response.json()["description"]
    assert "<script>" not in description
    assert "onerror" not in description
    assert "Texto" in description


def test_non_moderator_forbidden(auth_client, user, make_deck):
    deck = make_deck(name="Original")

    response = auth_client.patch(
        f"/api/v1/decks/{deck.id}/",
        {"name": "Hackeado"},
        content_type="application/json",
    )

    assert response.status_code == 403
    deck.refresh_from_db()
    assert deck.name == "Original"


def test_pending_moderator_forbidden(auth_client, user, make_deck):
    deck = make_deck(name="Original")
    _make_moderator(deck, user, status=DeckModerator.Status.PENDING)

    response = auth_client.patch(
        f"/api/v1/decks/{deck.id}/",
        {"name": "Hackeado"},
        content_type="application/json",
    )

    assert response.status_code == 403
    deck.refresh_from_db()
    assert deck.name == "Original"


def test_unauthenticated_rejected(api_client, make_deck):
    deck = make_deck(name="Original")

    response = api_client.patch(
        f"/api/v1/decks/{deck.id}/",
        {"name": "Hackeado"},
        content_type="application/json",
    )

    assert response.status_code in (401, 403)
    deck.refresh_from_db()
    assert deck.name == "Original"
