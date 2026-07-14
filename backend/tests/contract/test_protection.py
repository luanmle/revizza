"""Contract tests: per-deck field/tag protection (FR-040)."""

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def _url(deck):
    return f"/api/v1/decks/{deck.id}/protection/me/"


@pytest.fixture
def deck(make_note, subscribe):
    # nota dá ao deck um tipo de nota do qual derivar os field_names (T007/Decisão 4)
    deck = make_note().deck
    subscribe(deck)
    return deck


def test_get_and_replace_protection_config(auth_client, deck):
    empty = auth_client.get(_url(deck))
    assert empty.status_code == 200
    assert empty.json() == {"fields": [], "tags": []}

    saved = auth_client.put(
        _url(deck),
        {"fields": ["Frente"], "tags": ["pessoal", "favorita"]},
        format="json",
    )
    assert saved.status_code == 200
    assert saved.json() == {
        "fields": ["Frente"],
        "tags": ["pessoal", "favorita"],
    }

    replaced = auth_client.put(
        _url(deck), {"fields": ["Verso"], "tags": []}, format="json"
    )
    assert replaced.status_code == 200
    assert replaced.json() == {"fields": ["Verso"], "tags": []}


def test_rejects_unknown_fields_and_blank_tags(auth_client, deck):
    unknown = auth_client.put(
        _url(deck), {"fields": ["Inexistente"], "tags": ["pessoal"]}, format="json"
    )
    blank = auth_client.put(_url(deck), {"fields": [], "tags": ["  "]}, format="json")

    assert unknown.status_code == 400
    assert blank.status_code == 400


def test_protection_is_private_per_user(deck, make_user):
    other = make_user("outra@example.com")
    from apps.catalog.models import Subscription

    Subscription.objects.create(user=other, deck=deck)
    client = APIClient()
    client.force_authenticate(user=other)

    response = client.get(_url(deck))

    assert response.status_code == 200
    assert response.json() == {"fields": [], "tags": []}


def test_protection_requires_subscription(auth_client, make_deck):
    response = auth_client.get(_url(make_deck()))

    assert response.status_code == 403
