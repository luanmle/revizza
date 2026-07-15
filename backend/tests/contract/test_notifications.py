"""Contract test: notificações de decisão de sugestão e endpoints de leitura
(contracts/notifications.md, FR-001 a FR-008)."""

import pytest
from rest_framework.test import APIClient

from apps.notifications.models import Notification

pytestmark = pytest.mark.django_db


@pytest.fixture
def deck(make_deck):
    return make_deck()


@pytest.fixture
def suggestion(deck, make_note, make_suggestion, make_user):
    return make_suggestion(
        notes=[make_note(deck=deck)],
        author=make_user("autora@example.com"),
        proposed_field_values={"Verso": "Resposta corrigida"},
    )


@pytest.fixture
def moderator(make_user):
    return make_user("moderadora@example.com")


@pytest.fixture
def mod_client(moderator, deck, make_moderator):
    make_moderator(deck, moderator)
    client = APIClient()
    client.force_authenticate(user=moderator)
    return client


def test_accept_notifies_author(mod_client, suggestion):
    response = mod_client.post(f"/api/v1/suggestions/{suggestion.id}/accept/")

    assert response.status_code == 200
    notification = Notification.objects.get(
        recipient=suggestion.author, type=Notification.Type.SUGGESTION_ACCEPTED
    )
    assert notification.deck_id == suggestion.deck_id
    assert notification.suggestion_id == suggestion.id
    assert notification.read_at is None


def test_reject_notifies_author_with_reason(mod_client, suggestion):
    response = mod_client.post(
        f"/api/v1/suggestions/{suggestion.id}/reject/",
        {"rejection_reason": "duplicado"},
        format="json",
    )

    assert response.status_code == 200
    # exatamente uma notificação para essa decisão (não também um "accepted")
    assert Notification.objects.filter(suggestion=suggestion).count() == 1
    notification = Notification.objects.get(suggestion=suggestion)
    assert notification.type == Notification.Type.SUGGESTION_REJECTED
    from apps.notifications.serializers import NotificationSerializer

    data = NotificationSerializer(notification).data
    assert data["rejection_reason"] == "duplicado"


def test_decision_skips_notification_when_author_deleted(mod_client, suggestion):
    from apps.suggestions.models import Suggestion

    Suggestion.objects.filter(pk=suggestion.pk).update(author=None)
    suggestion.refresh_from_db()

    response = mod_client.post(f"/api/v1/suggestions/{suggestion.id}/accept/")

    assert response.status_code == 200
    assert Notification.objects.count() == 0


def test_mark_read_idempotent(auth_client, user, deck):
    notification = Notification.objects.create(
        recipient=user, type=Notification.Type.NEW_SUGGESTION, deck=deck
    )

    first = auth_client.post(f"/api/v1/notifications/{notification.id}/read/")
    notification.refresh_from_db()
    read_at = notification.read_at

    second = auth_client.post(f"/api/v1/notifications/{notification.id}/read/")
    notification.refresh_from_db()

    assert first.status_code == 204
    assert second.status_code == 204
    assert notification.read_at == read_at


def test_read_all_scoped_to_user(auth_client, user, deck, make_user):
    other = make_user("outra@example.com")
    mine = Notification.objects.create(
        recipient=user, type=Notification.Type.NEW_SUGGESTION, deck=deck
    )
    theirs = Notification.objects.create(
        recipient=other, type=Notification.Type.NEW_SUGGESTION, deck=deck
    )

    response = auth_client.post("/api/v1/notifications/read-all/")

    assert response.status_code == 204
    mine.refresh_from_db()
    theirs.refresh_from_db()
    assert mine.read_at is not None
    assert theirs.read_at is None


# --- US2: moderador sabe que há sugestão nova (FR-003) ---


def test_new_suggestion_notifies_moderators(deck, make_moderator, make_note, make_user):
    from apps.catalog.models import Subscription

    moderator = make_user("moderadora@example.com")
    make_moderator(deck, moderator)
    author_user = make_user("autora@example.com")
    Subscription.objects.create(user=author_user, deck=deck)
    author = APIClient()
    author.force_authenticate(user=author_user)
    note = make_note(deck=deck)

    response = author.post(
        f"/api/v1/notes/{note.id}/suggestions/change/",
        {
            "change_category": "erro_conteudo",
            "justification": "Justificativa de teste.",
            "proposed_field_values": {"Verso": "Nova resposta"},
        },
        format="json",
    )

    assert response.status_code == 201
    notification = Notification.objects.get(
        recipient=moderator, type=Notification.Type.NEW_SUGGESTION
    )
    assert notification.deck_id == deck.id


def test_new_suggestion_excludes_author_moderator(
    deck, make_moderator, make_note, make_user
):
    from apps.catalog.models import Subscription

    mod_user = make_user("moderadora@example.com")
    make_moderator(deck, mod_user)
    Subscription.objects.create(user=mod_user, deck=deck)
    client = APIClient()
    client.force_authenticate(user=mod_user)
    note = make_note(deck=deck)

    response = client.post(
        f"/api/v1/notes/{note.id}/suggestions/change/",
        {
            "change_category": "erro_conteudo",
            "justification": "Justificativa de teste.",
            "proposed_field_values": {"Verso": "Nova resposta"},
        },
        format="json",
    )

    assert response.status_code == 201
    assert not Notification.objects.filter(
        recipient=mod_user, type=Notification.Type.NEW_SUGGESTION
    ).exists()


def test_new_suggestion_no_moderators_noop(deck, make_note, make_user):
    from apps.catalog.models import Subscription

    author_user = make_user("autora@example.com")
    Subscription.objects.create(user=author_user, deck=deck)
    author = APIClient()
    author.force_authenticate(user=author_user)
    note = make_note(deck=deck)

    response = author.post(
        f"/api/v1/notes/{note.id}/suggestions/change/",
        {
            "change_category": "erro_conteudo",
            "justification": "Justificativa de teste.",
            "proposed_field_values": {"Verso": "Nova resposta"},
        },
        format="json",
    )

    assert response.status_code == 201
    assert not Notification.objects.filter(
        type=Notification.Type.NEW_SUGGESTION
    ).exists()


# --- US3: assinante sabe que há mudanças aguardando sincronização (FR-005/FR-006) ---


def test_accept_notifies_subscribers_sync_pending(mod_client, suggestion, subscribe, deck, user):
    subscribe(deck)

    response = mod_client.post(f"/api/v1/suggestions/{suggestion.id}/accept/")

    assert response.status_code == 200
    notification = Notification.objects.get(
        recipient=user, deck=deck, type=Notification.Type.SYNC_PENDING
    )
    assert notification.resolved_at is None


def test_sync_pending_deduplicated(
    mod_client, suggestion, subscribe, deck, user, make_note, make_suggestion
):
    subscribe(deck)
    second = make_suggestion(
        notes=[make_note(deck=deck)],
        author=suggestion.author,
        proposed_field_values={"Verso": "Outra resposta"},
    )

    mod_client.post(f"/api/v1/suggestions/{suggestion.id}/accept/")
    mod_client.post(f"/api/v1/suggestions/{second.id}/accept/")

    assert (
        Notification.objects.filter(
            recipient=user,
            deck=deck,
            type=Notification.Type.SYNC_PENDING,
            resolved_at__isnull=True,
        ).count()
        == 1
    )


def test_delta_sync_resolves_pending_notification(auth_client, user, deck, subscribe):
    subscribe(deck)
    notification = Notification.objects.create(
        recipient=user, deck=deck, type=Notification.Type.SYNC_PENDING
    )

    response = auth_client.get(f"/api/v1/decks/{deck.id}/sync/delta/")

    assert response.status_code == 200
    notification.refresh_from_db()
    assert notification.resolved_at is not None


def test_full_sync_resolves_pending_notification(auth_client, user, deck, subscribe):
    subscribe(deck)
    notification = Notification.objects.create(
        recipient=user, deck=deck, type=Notification.Type.SYNC_PENDING
    )

    response = auth_client.get(f"/api/v1/decks/{deck.id}/sync/full/")

    assert response.status_code == 200
    notification.refresh_from_db()
    assert notification.resolved_at is not None


def test_structural_change_delta_does_not_resolve_pending(
    auth_client, user, deck, subscribe, make_note, note_type
):
    from datetime import timedelta

    from django.utils import timezone

    subscribe(deck)
    make_note(deck=deck)
    note_type.structure_changed_at = timezone.now()
    note_type.save()
    notification = Notification.objects.create(
        recipient=user, deck=deck, type=Notification.Type.SYNC_PENDING
    )

    since = (timezone.now() - timedelta(days=1)).isoformat()
    response = auth_client.get(
        f"/api/v1/decks/{deck.id}/sync/delta/", {"since_mod": since}
    )

    assert response.status_code == 200
    assert response.json()["full_resync_required"] is True
    notification.refresh_from_db()
    assert notification.resolved_at is None


# --- Polish: contagem de não lidas e retenção (FR-010) ---


def test_unread_count(auth_client, user, deck):
    from django.utils import timezone

    Notification.objects.create(
        recipient=user, deck=deck, type=Notification.Type.NEW_SUGGESTION
    )
    Notification.objects.create(
        recipient=user,
        deck=deck,
        type=Notification.Type.NEW_SUGGESTION,
        read_at=timezone.now(),
    )

    response = auth_client.get("/api/v1/notifications/unread-count/")

    assert response.status_code == 200
    assert response.json() == {"count": 1}


def test_purge_read_notifications_command(user, deck):
    from datetime import timedelta

    from django.core.management import call_command
    from django.utils import timezone

    old_read = Notification.objects.create(
        recipient=user,
        deck=deck,
        type=Notification.Type.NEW_SUGGESTION,
        read_at=timezone.now() - timedelta(days=91),
    )
    recent_read = Notification.objects.create(
        recipient=user,
        deck=deck,
        type=Notification.Type.NEW_SUGGESTION,
        read_at=timezone.now(),
    )
    unread = Notification.objects.create(
        recipient=user, deck=deck, type=Notification.Type.NEW_SUGGESTION
    )

    call_command("purge_read_notifications")

    remaining = set(Notification.objects.values_list("id", flat=True))
    assert old_read.id not in remaining
    assert recent_read.id in remaining
    assert unread.id in remaining
