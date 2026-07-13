"""Contract test: GET /media/{content_hash}/ (contracts/sync.md, FR-036)."""

import pytest

from apps.catalog.models import Subscription
from apps.notes.models import MediaFile

pytestmark = pytest.mark.django_db

HASH = "a" * 64


@pytest.fixture
def media_file(make_deck):
    deck = make_deck()
    return MediaFile.objects.create(
        deck=deck,
        content_hash=HASH,
        storage_path=f"{deck.id}/{HASH}",
        original_filename="figura.png",
    )


def test_media_returns_signed_url_for_subscriber(
    auth_client, user, media_file, monkeypatch
):
    Subscription.objects.create(user=user, deck=media_file.deck)
    monkeypatch.setattr(
        "apps.sync.views.media.signed_download_url",
        lambda path: f"https://storage.example/{path}?signed",
    )

    response = auth_client.get(f"/api/v1/media/{HASH}/")

    assert response.status_code == 200
    body = response.json()
    assert body["url"].endswith("?signed")
    assert body["filename"] == "figura.png"


def test_media_requires_subscription_to_owning_deck(auth_client, media_file):
    assert auth_client.get(f"/api/v1/media/{HASH}/").status_code == 403


def test_media_unknown_hash_is_404(auth_client):
    assert auth_client.get(f"/api/v1/media/{'f' * 64}/").status_code == 404
