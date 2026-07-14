# Contract: `PATCH /api/v1/decks/{id}/`

Extends the existing `DeckDetailView` (currently `GET`-only). Auth required (existing session/token
middleware); no new auth scheme.

## Request

```
PATCH /api/v1/decks/{id}/
Content-Type: application/json

{
  "name": "string, optional, non-empty if present",
  "description": "string, optional (HTML allowed, sanitized server-side)",
  "subject_tags": ["string", "..."]  // optional, list of strings
}
```

Any subset of the three fields may be sent (partial update, FR-007).

## Responses

- **200 OK** — updated deck, same shape as `DeckDetailSerializer` (`GET /decks/{id}/`):
  ```json
  {
    "id": "uuid",
    "name": "...",
    "description": "...",
    "subject_tags": ["..."],
    "note_count": 0,
    "subscriber_count": 0,
    "created_at": "...",
    "moderator_count": 0,
    "is_moderator": true,
    "is_subscribed": true,
    "note_types": [...]
  }
  ```
- **400 Bad Request** — `name` present but empty/blank, or `subject_tags` present but not a list of
  strings:
  ```json
  { "detail": "..." }
  ```
- **403 Forbidden** — caller is not an active moderator of this deck (not authenticated, not a
  moderator, or moderator invite still `pending`) (FR-002):
  ```json
  { "detail": "Apenas moderadores ativos podem editar este deck." }
  ```
- **404 Not Found** — deck id does not exist (existing `get_object_or_404` behavior, unchanged).

## Side effects

- Updates `Deck.name`/`description`/`subject_tags` only. `Deck.anki_deck_name` is never written by
  this endpoint (FR-006) — it stays whatever was captured at publish time.
- No sync payload is emitted synchronously; the next regular sync (delta or full) for any subscriber
  picks up the new `description`/`subject_tags`/`name` **only insofar as those are surfaced by catalog
  reads** — the add-on's local deck placement continues to use `anki_deck_name`, unaffected by this
  endpoint (see research.md Decision 4).
