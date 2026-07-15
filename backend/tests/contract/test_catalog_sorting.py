from datetime import timedelta

import pytest
from django.utils import timezone

from apps.catalog.models import Deck, DeckModerator
from apps.catalog.views import CatalogPagination

pytestmark = pytest.mark.django_db

URL = "/api/v1/decks/"


def result_names(client, params=None):
    return [item["name"] for item in client.get(URL, params or {}).json()["results"]]


def set_created(deck, value):
    Deck.objects.filter(pk=deck.pk).update(created_at=value)


def test_all_public_sort_values(auth_client, user, make_deck, make_note):
    now = timezone.now()
    user.target_board = "fiscal"
    user.save(update_fields=["target_board"])
    recommended = make_deck(
        name="Recomendado", subject_tags=["fiscal"], subscriber_count=1, note_count=1
    )
    popular = make_deck(name="Popular", subscriber_count=20, note_count=2)
    updated = make_deck(name="Atualizado", subscriber_count=2, note_count=3)
    notes = make_deck(name="Mais notas", subscriber_count=3, note_count=30)
    recent = make_deck(name="Recente", subscriber_count=4, note_count=4)
    for index, deck in enumerate(
        [recommended, popular, updated, notes, recent], start=1
    ):
        set_created(deck, now - timedelta(days=10 - index))
        make_note(deck=deck, mod=now - timedelta(days=10 - index))
    make_note(deck=updated, mod=now)

    assert result_names(auth_client, {"sort": "recommended"})[0] == "Recomendado"
    assert result_names(auth_client, {"sort": "popular"})[0] == "Popular"
    assert result_names(auth_client, {"sort": "updated"})[0] == "Atualizado"
    assert result_names(auth_client, {"sort": "notes"})[0] == "Mais notas"
    assert result_names(auth_client, {"sort": "recent"})[0] == "Recente"


def test_invalid_sort_is_rejected(auth_client):
    response = auth_client.get(URL, {"sort": "email"})

    assert response.status_code == 400
    assert "sort" in response.json()


def test_sort_combines_with_tag_and_personal_tab(
    auth_client, user, make_deck, make_moderator
):
    low = make_deck(name="Baixo", subject_tags=["Direito"], subscriber_count=1)
    high = make_deck(name="Alto", subject_tags=["Direito"], subscriber_count=10)
    ignored = make_deck(
        name="Ignorado", subject_tags=["Português"], subscriber_count=100
    )
    for deck in [low, high, ignored]:
        make_moderator(deck, user, DeckModerator.Status.ACTIVE)

    assert result_names(
        auth_client, {"moderated": 1, "tag": "Direito", "sort": "popular"}
    ) == ["Alto", "Baixo"]


def test_cursor_pagination_is_stable(auth_client, make_deck, monkeypatch):
    monkeypatch.setattr(CatalogPagination, "page_size", 2)
    for name in ["A", "B", "C", "D", "E"]:
        make_deck(name=name, subscriber_count=1)

    first = auth_client.get(URL, {"sort": "popular"}).json()
    second = auth_client.get(first["next"]).json()
    first_ids = {item["id"] for item in first["results"]}
    second_ids = {item["id"] for item in second["results"]}

    assert len(first_ids) == len(second_ids) == 2
    assert first_ids.isdisjoint(second_ids)
