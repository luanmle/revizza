"""Contract test: GET /api/v1/decks/{id}/suggestions/ e GET /api/v1/suggestions/{id}/
(contracts/suggestions.md, FR-020 a FR-022)."""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.suggestions.models import Suggestion

pytestmark = pytest.mark.django_db


def _url(deck):
    return f"/api/v1/decks/{deck.id}/suggestions/"


def _ids(response):
    return {item["id"] for item in response.json()["results"]}


@pytest.fixture
def deck(make_deck, subscribe):
    deck = make_deck()
    subscribe(deck)
    return deck


def test_lists_deck_suggestions_cursor_paginated(
    auth_client, deck, make_note, make_suggestion
):
    suggestions = [make_suggestion(notes=[make_note(deck=deck)]) for _ in range(2)]

    response = auth_client.get(_url(deck))

    assert response.status_code == 200
    body = response.json()
    # convenção: paginação cursor com next/previous/results (api-conventions.md)
    assert set(body) >= {"next", "previous", "results"}
    assert {item["id"] for item in body["results"]} == {str(s.id) for s in suggestions}


def test_only_returns_suggestions_of_the_deck(
    auth_client, deck, make_deck, make_note, make_suggestion, subscribe
):
    mine = make_suggestion(notes=[make_note(deck=deck)])
    other_deck = make_deck(name="Outro")
    subscribe(other_deck)
    make_suggestion(notes=[make_note(deck=other_deck)])

    response = auth_client.get(_url(deck))

    assert _ids(response) == {str(mine.id)}


def test_filter_by_status(auth_client, deck, make_note, make_suggestion):
    pending = make_suggestion(notes=[make_note(deck=deck)])
    make_suggestion(notes=[make_note(deck=deck)], status=Suggestion.Status.REJECTED)

    response = auth_client.get(_url(deck), {"status": "pending"})

    assert response.status_code == 200
    assert _ids(response) == {str(pending.id)}


def test_filter_by_type(auth_client, deck, make_note, make_suggestion):
    make_suggestion(notes=[make_note(deck=deck)])
    deletion = make_suggestion(
        notes=[make_note(deck=deck)], type=Suggestion.Type.DELETION
    )

    response = auth_client.get(_url(deck), {"type": "deletion"})

    assert _ids(response) == {str(deletion.id)}


def test_filter_by_author(auth_client, deck, make_note, make_suggestion, make_user):
    other = make_user("outra@example.com")
    theirs = make_suggestion(notes=[make_note(deck=deck)], author=other)
    make_suggestion(notes=[make_note(deck=deck)])

    response = auth_client.get(_url(deck), {"author": str(other.id)})

    assert _ids(response) == {str(theirs.id)}


def test_filter_by_note_id(auth_client, deck, make_note, make_suggestion):
    note = make_note(deck=deck)
    on_note = make_suggestion(notes=[note])
    make_suggestion(notes=[make_note(deck=deck)])

    response = auth_client.get(_url(deck), {"note_id": str(note.id)})

    assert _ids(response) == {str(on_note.id)}


def test_filter_by_created_range(auth_client, deck, make_note, make_suggestion):
    old = make_suggestion(notes=[make_note(deck=deck)])
    recent = make_suggestion(notes=[make_note(deck=deck)])
    Suggestion.objects.filter(pk=old.pk).update(
        created_at=timezone.now() - timedelta(days=10)
    )
    cutoff = (timezone.now() - timedelta(days=1)).isoformat()

    after = auth_client.get(_url(deck), {"created_after": cutoff})
    before = auth_client.get(_url(deck), {"created_before": cutoff})

    assert _ids(after) == {str(recent.id)}
    assert _ids(before) == {str(old.id)}


def test_filter_by_submission_individual_vs_bulk(
    auth_client, deck, make_note, make_suggestion
):
    individual = make_suggestion(notes=[make_note(deck=deck)])
    bulk = make_suggestion(notes=[make_note(deck=deck), make_note(deck=deck)])

    r_individual = auth_client.get(_url(deck), {"submission": "individual"})
    r_bulk = auth_client.get(_url(deck), {"submission": "bulk"})

    assert _ids(r_individual) == {str(individual.id)}
    assert _ids(r_bulk) == {str(bulk.id)}


def test_list_is_public_read(auth_client, make_deck):
    # US3/contract §4: leitura pública — não-assinante lê (deep-link "Ver histórico")
    response = auth_client.get(_url(make_deck()))

    assert response.status_code == 200


def test_list_public_for_anonymous(api_client, make_deck):
    response = api_client.get(_url(make_deck()))

    assert response.status_code == 200


# --- Detalhe (FR-020) ---


def test_detail_returns_full_suggestion_with_like_count(
    auth_client, user, deck, make_note, make_suggestion, make_user
):
    from apps.suggestions.models import SuggestionVote

    note = make_note(deck=deck)
    user.name = "Ana Souza"
    user.save(update_fields=["name"])
    suggestion = make_suggestion(
        notes=[note], proposed_field_values={"Verso": "Corrigido"}
    )
    make_suggestion(notes=[note])
    voter = make_user("votante@example.com")
    SuggestionVote.objects.create(
        suggestion=suggestion, user=voter, value=SuggestionVote.Value.LIKE
    )

    response = auth_client.get(f"/api/v1/suggestions/{suggestion.id}/")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(suggestion.id)
    assert body["type"] == "change"
    assert body["status"] == "pending"
    assert body["author"] == str(user.id)
    assert body["author_name"] == "Ana Souza"
    assert body["avatar_url"] is None  # user sem avatar (007)
    assert body["justification"] == suggestion.justification
    assert body["proposed_field_values"] == {"Verso": "Corrigido"}
    assert body["note_ids"] == [str(note.id)]
    assert body["note_context"] == [
        {
            "id": str(note.id),
            "field_values": note.field_values,
            "tags": note.tags,
            "open_suggestion_count": 2,
        }
    ]
    assert body["likes_count"] == 1
    assert body["dislikes_count"] == 0
    assert "created_at" in body


def test_detail_requires_subscription(
    auth_client, make_deck, make_note, make_suggestion, make_user
):
    deck = make_deck()
    author = make_user("autora@example.com")
    suggestion = make_suggestion(notes=[make_note(deck=deck)], author=author)

    response = auth_client.get(f"/api/v1/suggestions/{suggestion.id}/")

    assert response.status_code == 403


def test_created_before_date_includes_whole_day(
    auth_client, deck, make_note, make_suggestion
):
    """FR-022/US5/AC2: data sem hora cobre o dia inteiro (T138)."""
    suggestion = make_suggestion(notes=[make_note(deck=deck)])  # criada agora
    today = timezone.now().date().isoformat()

    response = auth_client.get(_url(deck), {"created_before": today})

    assert _ids(response) == {str(suggestion.id)}


def test_list_query_count_is_bounded(
    auth_client,
    deck,
    make_note,
    make_suggestion,
    make_user,
    django_assert_max_num_queries,
):
    """FR-054: sem query por sugestão — contagens via annotate (T140)."""
    from apps.suggestions.models import SuggestionVote

    voter = make_user("votante@example.com")
    for _ in range(3):
        suggestion = make_suggestion(notes=[make_note(deck=deck), make_note(deck=deck)])
        SuggestionVote.objects.create(
            suggestion=suggestion, user=voter, value=SuggestionVote.Value.LIKE
        )

    with django_assert_max_num_queries(6):
        response = auth_client.get(_url(deck))

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3
    assert all(item["likes_count"] == 1 for item in results)
    assert all(item["dislikes_count"] == 0 for item in results)
    assert all(len(item["note_ids"]) == 2 for item in results)
