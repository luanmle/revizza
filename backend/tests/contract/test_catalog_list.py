"""Contract test: GET /api/v1/decks/ — lista/filtro/recomendação (contracts/catalog.md)."""

import pytest

pytestmark = pytest.mark.django_db

URL = "/api/v1/decks/"


def test_list_is_paginated_with_catalog_fields(auth_client, make_deck):
    make_deck(name="Direito Constitucional", subject_tags=["Direito"], note_count=10)

    response = auth_client.get(URL)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"next", "previous", "results"}
    deck = body["results"][0]
    # FR-006: nome, matéria/tags, nº de notas e nº de assinantes
    assert deck["name"] == "Direito Constitucional"
    assert deck["subject_tags"] == ["Direito"]
    assert deck["note_count"] == 10
    assert deck["subscriber_count"] == 0


def test_list_filters_by_tag(auth_client, make_deck):
    make_deck(name="A", subject_tags=["Português"])
    make_deck(name="B", subject_tags=["Direito"])

    response = auth_client.get(URL, {"tag": "português"})

    names = [d["name"] for d in response.json()["results"]]
    assert names == ["A"]  # FR-007, case-insensitive


def test_recommended_decks_come_first_for_matching_profile(
    auth_client, user, make_deck
):
    user.target_career = "fiscal"
    user.save()
    make_deck(name="Popular", subject_tags=["Português"], subscriber_count=100)
    make_deck(name="Fiscal", subject_tags=["Direito Fiscal"], subscriber_count=1)

    names = [d["name"] for d in auth_client.get(URL).json()["results"]]

    assert names == ["Fiscal", "Popular"]  # FR-008: recomendação no topo


def test_default_order_is_by_subscribers_without_profile(auth_client, make_deck):
    make_deck(name="Nicho", subject_tags=["Direito Fiscal"], subscriber_count=1)
    make_deck(name="Popular", subject_tags=["Português"], subscriber_count=100)

    names = [d["name"] for d in auth_client.get(URL).json()["results"]]

    assert names == ["Popular", "Nicho"]  # FR-008: fallback mais assinantes


def test_detail_includes_moderators(auth_client, user, make_deck):
    from apps.catalog.models import DeckModerator

    deck = make_deck(name="Com moderador")
    DeckModerator.objects.create(deck=deck, user=user, status="active")

    response = auth_client.get(f"{URL}{deck.id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Com moderador"
    assert body["moderators"] == [{"id": str(user.id), "email": user.email}]
    assert body["is_subscribed"] is False


def test_list_requires_authentication(api_client):
    assert api_client.get(URL).status_code == 401
