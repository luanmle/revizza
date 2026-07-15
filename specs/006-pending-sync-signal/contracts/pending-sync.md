# Contract: Pending Sync Signal (additive fields on existing endpoints)

Both fields are computed from the derived-state table in `data-model.md` — same underlying
`Notification.sync_pending` + `Subscription.last_synced_at`, no new source of truth.

## `GET /api/v1/decks/{id}/` (existing, `DeckDetailSerializer`)

Adds one field:

```json
{
  "...": "existing DeckDetailSerializer fields unchanged",
  "sync_status": "not_synced_yet"
}
```

- `sync_status` values: `"not_synced_yet"`, `"up_to_date"`, `"out_of_date"`, or `null`.
- `null` when `is_subscribed` is `false` (nothing to show for a non-subscriber).
- Requires authentication (same as today — `is_subscribed`/`is_moderator` already require
  `request.user`).

## `GET /api/v1/decks/?subscribed=1` (existing, `DeckSubscribedSerializer`, add-on only)

Adds one field per deck in `results`:

```json
{
  "...": "existing DeckSubscribedSerializer fields unchanged (id, name, ..., subscription)",
  "pending_sync": true
}
```

- `pending_sync` is `true` only for the `out_of_date` derived state (an active `sync_pending`
  Notification exists for this user+deck). `not_synced_yet` and `up_to_date` both serialize as
  `false` — the add-on menu only needs to know "does this deck need attention", the two-message
  distinction (onboarding vs. recurring) is a web-only concern (FR-002/FR-003 apply to the web
  surface; FR-005 applies to both).

## Non-goals

- No new endpoint added for either surface (Decision 3/4, research.md).
- No change to `POST /decks/{id}/sync/delta/` or `.../full/` response shape — `last_synced_at` is
  written as a side effect, not returned in that payload (mirrors how feature 005 resolved
  `sync_pending` without altering the sync response, Constitution Principle VIII).
