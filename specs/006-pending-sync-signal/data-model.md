# Phase 1 Data Model: Sinalização de Sincronização Pendente

## Changed entity: `Subscription` (`backend/apps/catalog/models.py`)

Add one field, no new table:

- `last_synced_at`: `DateTimeField(null=True, blank=True)` — timestamp of the subscriber's most
  recent successful delta/full sync of this deck. `None` means the subscriber has never completed a
  sync of this deck since subscribing.

**Write path**: set to `timezone.now()` in `apps/sync/views.py::_SubscriberSyncView.get`, right
alongside the existing `Notification` `sync_pending` resolution — same success condition (`not
status.is_client_error(...)` and not a `full_resync_required` redirect), but unconditional (runs
whether or not a `sync_pending` notification existed to resolve).

**No migration needed elsewhere**: `Notification` (feature 005) is reused as-is — no new fields, no
new model.

## Derived state: pending-sync signal (not persisted, computed per request)

For a given (user, deck) pair, three read-only derived states:

| `Subscription.last_synced_at` | Active `sync_pending` Notification | Derived state |
|---|---|---|
| `None` | — | `not_synced_yet` |
| set | exists | `out_of_date` |
| set | none | `up_to_date` (no indicator shown) |
| user not subscribed | — | `null` (no indicator, no data) |

This table is the single mapping both surfaces (web `sync_status` field, add-on `pending_sync` flag)
must implement identically — the add-on only needs the boolean collapse of `out_of_date` (`True`) vs.
`not_synced_yet`/`up_to_date` (`False`, per FR-005's "no false pending" and edge case "recently
subscribed, no accepted change yet ⇒ no add-on badge, only the web onboarding state applies").

## API surface changes (existing endpoints, new fields — see contracts/)

- `GET /decks/{id}/` (`DeckDetailSerializer`): `+ sync_status: "not_synced_yet" | "up_to_date" |
  "out_of_date" | null`.
- `GET /decks/?subscribed=1` (`DeckSubscribedSerializer`, consumed by the add-on): `+ pending_sync:
  bool`.

No new endpoints, no contract-breaking changes to either response shape (additive fields only).
