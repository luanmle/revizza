# API Contract: Notifications

All endpoints require authentication (existing session/auth convention — same as every other
`apps/*` endpoint). All queries are implicitly scoped to `recipient=request.user`; there is no
cross-user notification access by any endpoint.

## `GET /api/v1/notifications/`

Cursor-paginated list (`DefaultCursorPagination`, same `next`/`previous` shape as
`DeckSuggestionListView` and other existing list endpoints), ordered `-created_at`.

Query params:
- `unread` (optional, `true`/omitted) — when `true`, filters to `read_at__isnull=True`.

Response item shape:
```json
{
  "id": "uuid",
  "type": "suggestion_accepted | suggestion_rejected | new_suggestion | sync_pending",
  "deck_id": "uuid",
  "deck_name": "string",
  "suggestion_id": "uuid | null",
  "note_id": "uuid | null",
  "rejection_reason": "string | null",
  "read_at": "iso8601 | null",
  "created_at": "iso8601"
}
```
`rejection_reason` is populated only when `type == "suggestion_rejected"` (read live from the related
`Suggestion.rejection_reason`).

## `GET /api/v1/notifications/unread-count/`

```json
{"count": 0}
```
`count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()`.
Intended to be polled at a higher/independent frequency from the full list (badge vs. dropdown).

## `POST /api/v1/notifications/{id}/read/`

Marks one notification as read. 204 No Content on success. 404 if `id` doesn't belong to
`request.user`. Idempotent (re-marking an already-read notification is a no-op, still 204).

## `POST /api/v1/notifications/read-all/`

Marks every unread notification belonging to `request.user` as read. 204 No Content. Covers FR-008's
"or all at once."

No `PATCH`/`PUT`/`DELETE` endpoints — user-facing deletion is out of scope; retention (FR-010) is
handled by a management command (`purge_read_notifications`), not a user-triggered API call.

## Trigger points (not new endpoints — hooks into existing views)

| Existing view | File | Notification(s) created |
|---|---|---|
| `SuggestionDecisionView.post` (via `SuggestionAcceptView`/`SuggestionRejectView`) | `apps/suggestions/decisions.py` | one `suggestion_accepted`/`suggestion_rejected` to `suggestion.author` (skipped if `author_id is None`, i.e. author account deleted); on accept, also fans out `sync_pending` to every `Subscription` for `suggestion.deck` |
| `_create_change_suggestion`, `NewNoteSuggestionCreateView.post`, `DeletionSuggestionCreateView.post` | `apps/suggestions/views.py` | one `new_suggestion` per active `DeckModerator` of the deck, excluding the suggestion's own author |
| `_SubscriberSyncView.get` (base of `DeltaView`/`FullView`) | `apps/sync/views.py` | resolves (`resolved_at=now()`) any active `sync_pending` notification for `(request.user, deck)` after every successful sync call, regardless of whether the response contained any notes |
