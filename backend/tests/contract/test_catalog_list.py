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


def test_detail_exposes_only_non_sensitive_moderator_state(
    auth_client, user, make_deck
):
    from apps.catalog.models import DeckModerator

    deck = make_deck(name="Com moderador")
    DeckModerator.objects.create(deck=deck, user=user, status="active")

    response = auth_client.get(f"{URL}{deck.id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Com moderador"
    assert "moderators" not in body
    assert user.email not in str(body)
    assert body["moderator_count"] == 1
    assert body["is_moderator"] is True
    assert body["is_subscribed"] is False
    assert body["note_types"] == []


def test_detail_exposes_note_types_with_per_type_count(auth_client, make_note):
    from apps.notes.models import NoteType

    t1 = NoteType.objects.create(name="A", field_names=["F"], templates=[])
    t2 = NoteType.objects.create(name="B", field_names=["F"], templates=[])
    t3 = NoteType.objects.create(name="C", field_names=["F"], templates=[])
    note = make_note(note_type=t1)
    deck = note.deck
    make_note(deck=deck, note_type=t2)
    make_note(deck=deck, note_type=t2)
    make_note(deck=deck, note_type=t3)
    make_note(deck=deck, note_type=t3)
    make_note(deck=deck, note_type=t3)

    body = auth_client.get(f"{URL}{deck.id}/").json()

    counts = {t["name"]: t["note_count"] for t in body["note_types"]}
    assert counts == {"A": 1, "B": 2, "C": 3}  # FR-011: composição por tipo


def test_list_requires_authentication(api_client):
    assert api_client.get(URL).status_code == 401


def _store_raw_json_tags(deck, raw: str):
    """Simula o jsonb do Postgres, que normaliza \\uXXXX para o literal UTF-8."""
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE catalog_deck SET subject_tags = %s WHERE id = %s",
            [raw, deck.pk.hex],
        )


def test_filter_by_accented_tag_matches_escaped_storage(auth_client, make_deck):
    """FR-007/FR-056: sqlite persiste \\u00e7 — busca acentuada encontra (T132)."""
    make_deck(name="Licitações", subject_tags=["licitação"])

    response = auth_client.get(URL, {"tag": "licitação"})

    assert [d["name"] for d in response.json()["results"]] == ["Licitações"]


def test_filter_by_accented_tag_matches_literal_utf8_storage(auth_client, make_deck):
    """FR-007/FR-056: jsonb do Postgres guarda o literal UTF-8 (T132)."""
    deck = make_deck(name="Licitações", subject_tags=[])
    _store_raw_json_tags(deck, '["licitação"]')

    response = auth_client.get(URL, {"tag": "licitação"})

    assert [d["name"] for d in response.json()["results"]] == ["Licitações"]


def test_recommendation_matches_accented_profile_in_literal_storage(
    auth_client, user, make_deck
):
    user.target_board = "câmara"
    user.save()
    make_deck(name="Popular", subject_tags=["Português"], subscriber_count=100)
    deck = make_deck(name="Câmara", subject_tags=[], subscriber_count=1)
    _store_raw_json_tags(deck, '["concurso câmara"]')

    names = [d["name"] for d in auth_client.get(URL).json()["results"]]

    assert names == ["Câmara", "Popular"]  # FR-008 com acento no perfil (T132)
