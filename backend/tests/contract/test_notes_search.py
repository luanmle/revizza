"""Contract test: GET /api/v1/decks/{id}/notes/ e GET /api/v1/notes/{id}/
(contracts/notes.md, FR-010, FR-011)."""

import uuid

import pytest

pytestmark = pytest.mark.django_db


def _url(deck):
    return f"/api/v1/decks/{deck.id}/notes/"


def _ids(response):
    return {item["id"] for item in response.json()["results"]}


@pytest.fixture
def deck(make_deck, subscribe):
    deck = make_deck()
    subscribe(deck)
    return deck


def test_lists_deck_notes_cursor_paginated(auth_client, deck, make_note):
    notes = [make_note(deck=deck) for _ in range(2)]

    response = auth_client.get(_url(deck))

    assert response.status_code == 200
    body = response.json()
    assert set(body) >= {"next", "previous", "results"}
    assert {item["id"] for item in body["results"]} == {str(n.id) for n in notes}


def test_search_by_term_matches_field_content(auth_client, deck, make_note):
    hit = make_note(
        deck=deck, field_values={"Frente": "Prazo de licitação", "Verso": "15 dias"}
    )
    make_note(deck=deck, field_values={"Frente": "Outro tema", "Verso": "Nada"})

    response = auth_client.get(_url(deck), {"q": "licitação"})

    assert _ids(response) == {str(hit.id)}



def test_search_accented_term_matches_literal_utf8_storage(
    auth_client, deck, make_note
):
    """FR-010/FR-056: jsonb do Postgres guarda o literal UTF-8 (T132)."""
    from django.db import connection

    hit = make_note(deck=deck, field_values={"Frente": "x", "Verso": "y"})
    make_note(deck=deck)
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE notes_note SET field_values = %s WHERE id = %s",
            ['{"Frente": "Prazo de licitação", "Verso": "15 dias"}', hit.pk.hex],
        )

    response = auth_client.get(_url(deck), {"q": "licitação"})

    assert _ids(response) == {str(hit.id)}


def test_search_by_exact_note_id(auth_client, deck, make_note):
    hit = make_note(deck=deck)
    make_note(deck=deck)

    response = auth_client.get(_url(deck), {"note_id": str(hit.id)})

    assert _ids(response) == {str(hit.id)}


def test_invalid_note_id_returns_400(auth_client, deck):
    response = auth_client.get(_url(deck), {"note_id": "não-é-uuid"})

    assert response.status_code == 400


def test_excludes_soft_deleted_notes(auth_client, deck, make_note):
    from django.utils import timezone

    alive = make_note(deck=deck)
    make_note(deck=deck, deleted_at=timezone.now())

    response = auth_client.get(_url(deck))

    assert _ids(response) == {str(alive.id)}


def test_list_requires_subscription(auth_client, make_deck):
    response = auth_client.get(_url(make_deck()))

    assert response.status_code == 403


def test_list_requires_authentication(api_client, make_deck):
    response = api_client.get(_url(make_deck()))

    assert response.status_code == 401


# --- Detalhe (FR-011) ---


def test_detail_returns_fields_and_note_type_for_preview(
    auth_client, deck, make_note
):
    note = make_note(deck=deck, tags=["direito"])

    response = auth_client.get(f"/api/v1/notes/{note.id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(note.id)
    assert body["deck"] == str(deck.id)
    assert body["field_values"] == note.field_values
    assert body["tags"] == ["direito"]
    # o suficiente para o preview isolado (iframe srcDoc, research.md #13)
    assert body["note_type"]["field_names"] == ["Frente", "Verso"]
    assert "templates" in body["note_type"]
    assert "css" in body["note_type"]


def test_detail_requires_subscription(auth_client, make_note):
    note = make_note()

    response = auth_client.get(f"/api/v1/notes/{note.id}/")

    assert response.status_code == 403


def test_detail_unknown_note_returns_404(auth_client, deck):
    response = auth_client.get(f"/api/v1/notes/{uuid.uuid4()}/")

    assert response.status_code == 404
