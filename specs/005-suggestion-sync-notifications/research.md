# Phase 0 Research: Notificações de Suggestion/Sync

No `[NEEDS CLARIFICATION]` markers remained in spec.md after `/speckit-specify` (the one open question —
retention period, FR-010 — was resolved with the user: 90 days). The one open implementation-level
question below is a design choice, not a spec gap.

## Decision 1: Where does "sync pending" state live?

**Decision**: The `Notification` row itself is the source of truth for `sync_pending`. It is created
when a suggestion is accepted (`apps/suggestions/decisions.py::SuggestionAcceptView`) for every
subscriber of that deck, and resolved (`resolved_at` set) the next time that subscriber successfully
calls `DeltaView` or `FullView` in `apps/sync/views.py`.

**Rationale**:
- Avoids a second source of truth. The alternative (a `last_synced_at` field on
  `apps.catalog.Subscription`, compared against the deck's most recent note `mod`) requires computing
  `MAX(note.mod)` per subscriber on every notification-list/unread-count poll — heavier than reading a
  boolean-ish `resolved_at IS NULL` off an already-indexed table.
- Keeps `apps/sync/views.py` changes to a single `.update()` scoped to the new `Notification` table,
  which is the cleanest way to satisfy Constitution Principle VIII (Sync Fidelity & State Separation):
  the sync endpoints' existing behavior — reading/returning Note/NoteType/Card-adjacent payload data —
  is untouched; the added line only ever writes to `Notification`.
- The DB-level partial unique constraint (see data-model.md) on `(recipient, deck)` for
  `type=sync_pending, resolved_at IS NULL` gives FR-005's "at most one active notification" guarantee
  for free via `get_or_create`, no app-level locking needed.

**Alternatives considered**:
- `Subscription.last_synced_at` + compare-to-max-mod at read time — rejected: duplicate state (the
  fact "is there anything unsynced" would exist in two places that could drift), and heavier per-poll
  query cost for no behavioral gain.
- Deriving "pending" purely from `Suggestion.status=ACCEPTED AND decided_at > subscriber's last sync`
  without persisting anything — rejected: there is no persisted "last sync" timestamp per subscriber
  anywhere today (`DeltaView` takes a client-supplied `since_mod` query param, not a server-stored
  cursor), so this alternative still requires adding new persisted state; it just moves the same
  problem without simplifying it.

## Decision 2: Signals vs. explicit calls for notification creation

**Decision**: Explicit function calls (`notify_suggestion_decided`, `notify_new_suggestion` in
`apps/notifications/services.py`) inserted directly into the existing view/transaction bodies, not
Django `post_save` signals.

**Rationale**: `apps/suggestions/decisions.py` and `apps/suggestions/views.py` already perform
explicit multi-step work inside `transaction.atomic()` blocks (row locks, denormalized counters). A
signal handler reacting to `Suggestion.save()` would fire on every save (including the earlier
`suggestion.decided_by = request.user; suggestion.save()` inside the same view) and obscure exactly
when a notification is created — an explicit call at the right point in the existing transaction is
one line, self-documenting, and matches Principle VI (minimal, current code, no hidden control flow).

**Alternatives considered**: Django signals (`post_save` on `Suggestion`) — rejected for the reason
above; would also require a signal-vs-explicit-save disambiguation (e.g. a dirty-field check) to avoid
double-firing, which is strictly more code than the explicit call.

## Decision 3: Notification model shape — concrete FKs vs. GenericForeignKey

**Decision**: Concrete nullable FKs (`deck` always set, `suggestion`/`note` nullable depending on
`type`), not `GenericForeignKey`.

**Rationale**: Exactly 4 fixed notification types exist per the spec; `GenericForeignKey` buys
polymorphism for an open-ended set of referenced models, which this feature doesn't have and isn't
expected to grow (YAGNI). `apps/discussions/models.py`'s `Comment` model already uses the "nullable FK
per variant + constraint" pattern in this codebase, so this is Parity Over Reinvention, not a new
pattern.
