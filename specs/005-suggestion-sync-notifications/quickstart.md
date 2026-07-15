# Quickstart: Notificações de Suggestion/Sync

Validation scenarios to run once the feature is implemented (backend `pytest`, or manual API calls
against a local server). References: [data-model.md](./data-model.md), [contracts/notifications.md](./contracts/notifications.md).

## Prerequisites

- Local backend running with a deck that has: one moderator (`M`), one subscriber who is not the
  moderator (`S`), and one suggestion author (`A`, distinct from `M` and `S`).
- Auth tokens/sessions for `M`, `S`, `A`.

## Scenario 1 — Decision notifies the author; acceptance notifies subscribers of pending sync

1. As `A`, submit a change suggestion on a note in the deck (`POST /api/v1/notes/{note_id}/suggestions/`
   or equivalent existing creation endpoint).
2. As `M`, accept it (`POST /api/v1/suggestions/{id}/accept/`).
3. As `A`, `GET /api/v1/notifications/?unread=true` → expect one `suggestion_accepted` entry
   referencing the deck/suggestion, `read_at: null`.
4. As `S`, `GET /api/v1/notifications/?unread=true` → expect one `sync_pending` entry for the deck,
   `read_at: null`, no `suggestion`/`note` id required.
5. As `S`, call `GET /decks/{deck_id}/sync/delta/` (real sync call).
6. As `S`, `GET /api/v1/notifications/?unread=true` again → the `sync_pending` entry is gone from the
   unread-pending set (confirm via a direct model check that `resolved_at` is now set) — FR-006.
7. Repeat steps 1-2 with a second suggestion accepted before `S` syncs → confirm `S` still has exactly
   one active `sync_pending` notification (FR-005/SC-004), not two.

## Scenario 2 — New suggestion notifies moderators, not the author-moderator

1. As `A` (not a moderator), submit a new suggestion on the deck.
2. As `M`, `GET /api/v1/notifications/?unread=true` → expect one `new_suggestion` entry.
3. Repeat with `M` as the suggestion's author instead of `A` → `M` must NOT receive a `new_suggestion`
   notification for their own submission (edge case in spec.md).

## Scenario 3 — Rejection carries the reason

1. As `A`, submit a suggestion.
2. As `M`, reject it with `rejection_reason: "duplicado"`
   (`POST /api/v1/suggestions/{id}/reject/`).
3. As `A`, `GET /api/v1/notifications/` → the `suggestion_rejected` entry's `rejection_reason` field
   equals `"duplicado"`.

## Scenario 4 — Mark as read

1. As `A`, `POST /api/v1/notifications/{id}/read/` on the entry from Scenario 3.
2. `GET /api/v1/notifications/unread-count/` → `count` decreases by 1.
3. `POST /api/v1/notifications/read-all/` with other unread entries present → `unread-count` becomes 0.
