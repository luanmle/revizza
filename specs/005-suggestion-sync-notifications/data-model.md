# Phase 1 Data Model: Notificações de Suggestion/Sync

## `Notification` (new — `apps/notifications/models.py`, inherits `apps.base.BaseModel`)

| Field | Type | Notes |
|---|---|---|
| `id` | UUID (pk) | from `BaseModel` |
| `created_at` / `updated_at` | datetime | from `BaseModel` |
| `recipient` | FK → `accounts.User`, `on_delete=CASCADE`, `related_name="notifications"` | who sees this notification |
| `type` | `CharField(choices=Type)` | `suggestion_accepted`, `suggestion_rejected`, `new_suggestion`, `sync_pending` |
| `deck` | FK → `catalog.Deck`, `on_delete=CASCADE`, `related_name="notifications"` | always set — every notification is deck-scoped |
| `suggestion` | FK → `suggestions.Suggestion`, `on_delete=CASCADE`, `null=True, blank=True` | set for `suggestion_accepted`/`suggestion_rejected`/`new_suggestion`; null for `sync_pending` |
| `note` | FK → `notes.Note`, `on_delete=CASCADE`, `null=True, blank=True` | set only when the suggestion targets exactly one existing note; null for new-note suggestions, `sync_pending`, and bulk suggestions targeting multiple notes (FR-001 — bulk decisions reference deck+suggestion only) |
| `read_at` | `DateTimeField(null=True, blank=True)` | null = unread |
| `resolved_at` | `DateTimeField(null=True, blank=True)` | only meaningful for `sync_pending`; null = still pending |

**Indexes**: `(recipient, read_at, created_at)` — supports the list/unread-count queries (`WHERE
recipient=... AND read_at IS NULL ORDER BY created_at`).

**Constraints**: partial `UniqueConstraint` on `(recipient, deck)` where `type="sync_pending" AND
resolved_at IS NULL` — enforces FR-005 ("at most one active sync-pending notification per
subscriber/deck") at the database level; `notify_suggestion_decided`'s fan-out uses
`get_or_create(..., defaults=...)` against this same predicate, so a second `ACCEPT` on the same deck
before the subscriber syncs is a no-op (no new row, no error).

**Deliberately excluded field**: a denormalized copy of `Suggestion.rejection_reason`. It's read live
via the `suggestion` FK at serialization time — `rejection_reason` is immutable once a suggestion
reaches a terminal (`ACCEPTED`/`REJECTED`) status (see `apps/suggestions/decisions.py`), so there is no
staleness risk, and this avoids a second copy of the same fact (Principle VI).

**Deliberately excluded**: no `GenericForeignKey` (see research.md Decision 3), no separate
"NotificationPreference" model (no spec requirement for per-user opt-out of in-app notifications — out
of scope / YAGNI), no soft-delete (retention is a hard-delete management command per FR-010, not a
per-row `deleted_at`).

## Relationships to existing entities (no schema change to these — reference only)

- `Suggestion` (`apps/suggestions/models.py`): `status` transition (`PENDING` → `ACCEPTED`/`REJECTED`)
  in `SuggestionDecisionView.post` is the trigger for `notify_suggestion_decided`.
- `DeckModerator` (`apps/catalog/models.py`): `status=ACTIVE` rows for a deck are the recipients of
  `new_suggestion` notifications (excluding the suggestion's own author).
- `Subscription` (`apps/catalog/models.py`): rows for a deck (excluding the accepted suggestion's
  author is NOT applied here — a subscriber who authored the accepted change still has an unsynced
  local collection) are the recipients of `sync_pending` notifications.

## State transitions

```text
Notification (suggestion_accepted / suggestion_rejected / new_suggestion):
  created (read_at=NULL) --[user marks read]--> read_at=now()  [terminal]

Notification (sync_pending):
  created (resolved_at=NULL, read_at=NULL)
    --[user marks read]--> read_at=now() (still resolved_at=NULL, i.e. read but still pending)
    --[subscriber's next successful DeltaView/FullView call]--> resolved_at=now() [terminal regardless of read_at]
```
