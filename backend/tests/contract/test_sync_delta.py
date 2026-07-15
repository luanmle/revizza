"""Contract test: GET /decks/{id}/sync/delta/ (contracts/sync.md, FR-031/034/035, FR-032)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.catalog.models import Subscription
from apps.notes.models import Note, NoteType

pytestmark = pytest.mark.django_db


def _url(deck):
    return f"/api/v1/decks/{deck.id}/sync/delta/"


def _make_note(deck, note_type, guid, mod, **kwargs):
    return Note.objects.create(
        deck=deck,
        note_type=note_type,
        guid=guid,
        field_values=kwargs.pop("field_values", {"Frente": "Q", "Verso": "A"}),
        tags=kwargs.pop("tags", []),
        mod=mod,
        **kwargs,
    )


@pytest.fixture
def subscribed_deck(make_deck, user):
    deck = make_deck(name="Deck Sync")
    Subscription.objects.create(user=user, deck=deck)
    return deck


def test_delta_returns_only_changes_since_mod(auth_client, subscribed_deck, note_type):
    now = timezone.now()
    _make_note(subscribed_deck, note_type, "old", now - timedelta(days=2))
    _make_note(subscribed_deck, note_type, "new", now, anki_deck_path="Sub::Nível 2")
    _make_note(
        subscribed_deck, note_type, "gone", now, deleted_at=now
    )  # remoção propagada (FR-037)

    since = (now - timedelta(days=1)).isoformat()
    response = auth_client.get(_url(subscribed_deck), {"since_mod": since})

    assert response.status_code == 200
    body = response.json()
    assert body["full_resync_required"] is False
    assert body["deck_name"] == "Deck Sync"
    # seções na ordem de aplicação do add-on (FR-034)
    assert [nt["name"] for nt in body["note_types"]] == ["Básico"]
    by_guid = {n["guid"]: n for n in body["notes"]}
    assert set(by_guid) == {"new", "gone"}
    assert by_guid["gone"]["deleted"] is True
    assert by_guid["new"]["anki_deck_path"] == "Sub::Nível 2"
    assert body["subdecks"] == ["Sub::Nível 2"]


def test_delta_without_since_mod_returns_everything(
    auth_client, subscribed_deck, note_type
):
    _make_note(subscribed_deck, note_type, "a", timezone.now())

    body = auth_client.get(_url(subscribed_deck)).json()

    assert [n["guid"] for n in body["notes"]] == ["a"]


def test_delta_flags_full_resync_on_structural_change(
    auth_client, subscribed_deck, note_type
):
    _make_note(subscribed_deck, note_type, "a", timezone.now())
    note_type.structure_changed_at = timezone.now()
    note_type.save()

    since = (timezone.now() - timedelta(days=1)).isoformat()
    body = auth_client.get(_url(subscribed_deck), {"since_mod": since}).json()

    assert body["full_resync_required"] is True  # FR-035
    assert body["notes"] == []
    assert (
        auth_client.get(f"/api/v1/decks/{subscribed_deck.id}/sync/full/").status_code
        == 200
    )  # cliente anterior ainda consegue concluir o fallback uma vez


def test_delta_full_resync_when_one_type_of_multi_type_deck_changes(
    auth_client, subscribed_deck, note_type
):
    """US2: mudança estrutural em UM dos tipos de um deck multi-tipo força full resync."""
    cloze = NoteType.objects.create(
        name="Cloze BR", field_names=["Texto"], templates=[{"name": "Cloze"}]
    )
    _make_note(subscribed_deck, note_type, "basica", timezone.now())
    _make_note(subscribed_deck, cloze, "cloze", timezone.now(),
               field_values={"Texto": "x"})
    cloze.structure_changed_at = timezone.now()  # só o segundo tipo mudou
    cloze.save()

    since = (timezone.now() - timedelta(days=1)).isoformat()
    body = auth_client.get(_url(subscribed_deck), {"since_mod": since}).json()

    assert body["full_resync_required"] is True  # FR-035
    assert body["notes"] == []


def test_notification_resolution_does_not_alter_sync_payload(
    auth_client, subscribed_deck, note_type, user
):
    """Principle VIII: resolver sync_pending não altera o payload de sync."""
    from apps.notifications.models import Notification

    _make_note(subscribed_deck, note_type, "a", timezone.now())
    Notification.objects.create(
        recipient=user, deck=subscribed_deck, type=Notification.Type.SYNC_PENDING
    )

    with_pending = auth_client.get(_url(subscribed_deck)).json()

    Notification.objects.create(
        recipient=user, deck=subscribed_deck, type=Notification.Type.SYNC_PENDING
    )
    auth_client.credentials(HTTP_X_SYNC_RUN_ID="run-1")
    without_pending = auth_client.get(_url(subscribed_deck)).json()

    assert with_pending == without_pending


def test_delta_is_rate_limited_to_one_per_10s(auth_client, subscribed_deck):
    assert auth_client.get(_url(subscribed_deck)).status_code == 200

    response = auth_client.get(_url(subscribed_deck))

    assert response.status_code == 429  # FR-032
    assert response.headers["Retry-After"] == "10"


def test_sync_run_covers_multiple_decks_and_full_fallback(
    auth_client, subscribed_deck, make_deck, user
):
    second_deck = make_deck(name="Outro Deck")
    Subscription.objects.create(user=user, deck=second_deck)
    auth_client.credentials(HTTP_X_SYNC_RUN_ID="run-1")

    assert auth_client.get(_url(subscribed_deck)).status_code == 200
    assert auth_client.get(_url(second_deck)).status_code == 200
    assert (
        auth_client.get(f"/api/v1/decks/{subscribed_deck.id}/sync/full/").status_code
        == 200
    )

    auth_client.credentials(HTTP_X_SYNC_RUN_ID="run-2")
    assert (
        auth_client.get(f"/api/v1/decks/{subscribed_deck.id}/sync/full/").status_code
        == 429
    )


def test_delta_requires_subscription(auth_client, make_deck):
    deck = make_deck()

    assert auth_client.get(_url(deck)).status_code == 403


def test_delta_rejects_invalid_since_mod(auth_client, subscribed_deck):
    response = auth_client.get(_url(subscribed_deck), {"since_mod": "ontem"})

    assert response.status_code == 400


def test_delta_accepts_naive_since_mod_as_utc(auth_client, subscribed_deck, note_type):
    """FR-034: ISO 8601 sem timezone é tratado como UTC (T131)."""
    now = timezone.now()
    _make_note(subscribed_deck, note_type, "old", now - timedelta(days=2))
    _make_note(subscribed_deck, note_type, "new", now)

    naive = (now - timedelta(days=1)).replace(tzinfo=None).isoformat()
    response = auth_client.get(_url(subscribed_deck), {"since_mod": naive})

    assert response.status_code == 200
    assert {n["guid"] for n in response.json()["notes"]} == {"new"}
