"""Contract test: GET /media/{content_hash}/ (contracts/sync.md, FR-036)."""

import pytest
from django.test import override_settings
from django.core.cache import cache

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


@override_settings(RATELIMIT_MEDIA_RATE="3/m")
def test_media_url_issuance_is_rate_limited_per_user(
    auth_client, user, media_file, monkeypatch
):
    cache.clear()
    Subscription.objects.create(user=user, deck=media_file.deck)
    monkeypatch.setattr(
        "apps.sync.views.media.signed_download_url", lambda path: "https://s/x"
    )

    # fan-out legítimo de um sync run passa dentro do rate configurado (T133)
    for _ in range(3):
        assert auth_client.get(f"/api/v1/media/{HASH}/").status_code == 200

    blocked = auth_client.get(f"/api/v1/media/{HASH}/")
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == "60"


# --- T007: status-gating de mídia (011, contracts/media-sync.md §1/§2/§4) ---

PENDING_HASH = "b" * 64


@pytest.fixture
def pending_media(make_deck):
    deck = make_deck()
    return MediaFile.objects.create(
        deck=deck,
        content_hash=PENDING_HASH,
        storage_path=f"{deck.id}/{PENDING_HASH}",
        original_filename="pendente.png",
        status="pending_upload",
    )


def test_download_of_pending_upload_hash_is_404(auth_client, user, pending_media):
    # mesmo 404 de hash desconhecido: o cliente não distingue "nunca vai existir"
    # de "ainda não pronto" (§2)
    Subscription.objects.create(user=user, deck=pending_media.deck)
    response = auth_client.get(f"/api/v1/media/{PENDING_HASH}/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Mídia ainda não disponível."


def test_confirm_flips_status_and_is_idempotent(auth_client, user, pending_media):
    from apps.catalog.models import DeckModerator

    DeckModerator.objects.create(
        deck=pending_media.deck, user=user, status=DeckModerator.Status.ACTIVE
    )
    url = f"/api/v1/decks/{pending_media.deck.id}/media/{PENDING_HASH}/confirm/"

    first = auth_client.post(url)
    assert first.status_code == 200
    assert first.json() == {"content_hash": PENDING_HASH, "status": "ready"}
    pending_media.refresh_from_db()
    assert pending_media.status == "ready"

    # repetição é no-op 200, não erro (FR-004 resumability)
    again = auth_client.post(url)
    assert again.status_code == 200
    assert again.json()["status"] == "ready"


def test_confirm_requires_creator_or_moderator(auth_client, pending_media):
    url = f"/api/v1/decks/{pending_media.deck.id}/media/{PENDING_HASH}/confirm/"
    response = auth_client.post(url)
    assert response.status_code == 403


def test_confirm_unknown_hash_for_deck_is_404(auth_client, user, make_deck):
    from apps.catalog.models import DeckModerator

    deck = make_deck()
    DeckModerator.objects.create(
        deck=deck, user=user, status=DeckModerator.Status.ACTIVE
    )
    url = f"/api/v1/decks/{deck.id}/media/{'c' * 64}/confirm/"
    response = auth_client.post(url)
    assert response.status_code == 404


def test_delta_and_full_never_list_pending_upload_hash(
    auth_client, user, pending_media
):
    from django.utils import timezone

    from apps.notes.models import Note, NoteType

    deck = pending_media.deck
    Subscription.objects.create(user=user, deck=deck)
    ready = MediaFile.objects.create(
        deck=deck,
        content_hash="d" * 64,
        storage_path=f"{deck.id}/{'d' * 64}",
        original_filename="ok.png",
        status="ready",
    )
    nt = NoteType.objects.create(
        name="Básico", field_names=["Frente", "Verso"], templates=[], css=""
    )
    Note.objects.create(
        deck=deck,
        note_type=nt,
        guid="n1",
        field_values={"Frente": "Q", "Verso": "A"},
        tags=[],
        mod=timezone.now(),
    )

    cache.clear()
    for path in ("delta", "full"):
        # mesmo run id: delta e full do mesmo sync run passam a guarda de 10s
        body = auth_client.get(
            f"/api/v1/decks/{deck.id}/sync/{path}/", HTTP_X_SYNC_RUN_ID="run-1"
        ).json()
        hashes = {m["content_hash"] for m in body["media"]}
        assert ready.content_hash in hashes
        assert PENDING_HASH not in hashes


def test_publish_issues_upload_urls_then_confirm_exposes_media(
    auth_client, user, monkeypatch
):
    """T020: publish emite URL só para hash inédito; após confirm, delta/full o listam."""
    import uuid

    from apps.catalog.models import Deck, Subscription

    cache.clear()
    monkeypatch.setattr(
        "apps.sync.views.media.signed_upload_url", lambda path: f"https://up/{path}"
    )
    hash_a = "1" * 64
    deck_id = str(uuid.uuid4())
    payload = {
        "name": "Deck Mídia",
        "note_types": [
            {
                "name": "Básico",
                "field_names": ["Frente", "Verso"],
                "templates": [
                    {"name": "Card 1", "qfmt": "{{Frente}}", "afmt": "{{Verso}}"}
                ],
                "css": "",
            }
        ],
        "notes": [
            {
                "guid": "n1",
                "field_values": {"Frente": '<img src="fig.png">', "Verso": "A"},
                "tags": [],
                "anki_deck_path": "",
                "note_type_index": 0,
            }
        ],
        "media": [{"filename": "fig.png", "content_hash": hash_a}],
    }

    published = auth_client.post(
        f"/api/v1/decks/{deck_id}/publish/", payload, format="json"
    )
    assert published.status_code == 201
    # URL emitida só para o hash inédito
    assert set(published.json()["media_upload_urls"]) == {hash_a}

    deck = Deck.objects.get(pk=deck_id)
    Subscription.objects.create(user=user, deck=deck)

    # antes do confirm o hash está pending_upload → ausente do manifesto (§1)
    cache.clear()
    before = auth_client.get(
        f"/api/v1/decks/{deck_id}/sync/full/", HTTP_X_SYNC_RUN_ID="r0"
    ).json()
    assert before["media"] == []

    auth_client.post(f"/api/v1/decks/{deck_id}/media/{hash_a}/confirm/")

    cache.clear()
    for path in ("delta", "full"):
        body = auth_client.get(
            f"/api/v1/decks/{deck_id}/sync/{path}/", HTTP_X_SYNC_RUN_ID="r1"
        ).json()
        assert {m["content_hash"] for m in body["media"]} == {hash_a}


# --- POST /decks/{id}/media/ — slots de upload para mídia de sugestões (US2) ---

NEW_HASH = "c" * 64


@pytest.fixture
def suggestion_media_deck(make_deck):
    return make_deck()


def _request_media(client, deck, items):
    return client.post(
        f"/api/v1/decks/{deck.id}/media/", {"media": items}, format="json"
    )


def test_media_request_requires_subscription(auth_client, suggestion_media_deck):
    response = _request_media(
        auth_client,
        suggestion_media_deck,
        [{"filename": "nova.png", "content_hash": NEW_HASH}],
    )
    assert response.status_code == 403


def test_media_request_returns_upload_url_for_new_hash(
    auth_client, user, suggestion_media_deck, monkeypatch
):
    Subscription.objects.create(user=user, deck=suggestion_media_deck)
    monkeypatch.setattr(
        "apps.sync.views.media.signed_upload_url",
        lambda path: f"https://storage.example/{path}?upload",
    )

    response = _request_media(
        auth_client,
        suggestion_media_deck,
        [{"filename": "nova.png", "content_hash": NEW_HASH}],
    )

    assert response.status_code == 200
    assert response.json()["media_upload_urls"][NEW_HASH].endswith("?upload")
    row = MediaFile.objects.get(deck=suggestion_media_deck, content_hash=NEW_HASH)
    assert row.status == "pending_upload"
    assert row.original_filename == "nova.png"


def test_media_request_skips_ready_hash(auth_client, user, suggestion_media_deck):
    Subscription.objects.create(user=user, deck=suggestion_media_deck)
    MediaFile.objects.create(
        deck=suggestion_media_deck,
        content_hash=NEW_HASH,
        storage_path=f"{suggestion_media_deck.id}/{NEW_HASH}",
        original_filename="ja-existe.png",
        status="ready",
    )

    response = _request_media(
        auth_client,
        suggestion_media_deck,
        [{"filename": "ja-existe.png", "content_hash": NEW_HASH}],
    )

    assert response.status_code == 200
    assert response.json()["media_upload_urls"] == {}


def test_media_request_rejects_bad_hash(auth_client, user, suggestion_media_deck):
    Subscription.objects.create(user=user, deck=suggestion_media_deck)
    response = _request_media(
        auth_client,
        suggestion_media_deck,
        [{"filename": "x.png", "content_hash": "../../etc/passwd"}],
    )
    assert response.status_code == 400


def test_subscriber_can_confirm_suggestion_media(
    auth_client, user, suggestion_media_deck
):
    Subscription.objects.create(user=user, deck=suggestion_media_deck)
    MediaFile.objects.create(
        deck=suggestion_media_deck,
        content_hash=NEW_HASH,
        storage_path=f"{suggestion_media_deck.id}/{NEW_HASH}",
        original_filename="nova.png",
        status="pending_upload",
    )

    response = auth_client.post(
        f"/api/v1/decks/{suggestion_media_deck.id}/media/{NEW_HASH}/confirm/"
    )

    assert response.status_code == 200
    row = MediaFile.objects.get(deck=suggestion_media_deck, content_hash=NEW_HASH)
    assert row.status == "ready"
