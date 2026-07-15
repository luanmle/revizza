import pytest

from apps.catalog.models import DeckModerator, Subscription

pytestmark = pytest.mark.django_db

URL = "/api/v1/decks/"


def names(response):
    return [deck["name"] for deck in response.json()["results"]]


def test_anonymous_catalog_is_public_but_personal_tabs_require_login(
    api_client, make_deck
):
    make_deck(name="Público")

    assert names(api_client.get(URL)) == ["Público"]
    assert api_client.get(URL, {"moderated": 1}).status_code == 401
    assert api_client.get(URL, {"subscribed": 1}).status_code == 401


def test_moderated_lists_only_active_moderation(
    auth_client, user, make_user, make_deck, make_moderator
):
    active = make_deck(name="Ativo")
    pending = make_deck(name="Pendente")
    other = make_deck(name="Outro")
    make_moderator(active, user)
    make_moderator(pending, user, DeckModerator.Status.PENDING)
    make_moderator(other, make_user("outro@example.com"))

    assert names(auth_client.get(URL, {"moderated": 1})) == ["Ativo"]


def test_subscribed_combines_with_tag_and_can_be_empty(auth_client, user, make_deck):
    direito = make_deck(name="Direito", subject_tags=["Direito"])
    make_deck(name="Português", subject_tags=["Português"])
    Subscription.objects.create(user=user, deck=direito)

    assert names(auth_client.get(URL, {"subscribed": 1, "tag": "Direito"})) == [
        "Direito"
    ]
    assert names(auth_client.get(URL, {"subscribed": 1, "tag": "Inexistente"})) == []


def test_subscribed_and_moderated_are_mutually_exclusive(auth_client):
    response = auth_client.get(URL, {"subscribed": 1, "moderated": 1})

    assert response.status_code == 400
    assert "subscribed" in str(response.json())
