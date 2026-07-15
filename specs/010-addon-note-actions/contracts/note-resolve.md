# Contract: GUID Resolution & Public Read Endpoints

New/changed backend endpoints on the `notes` and `suggestions` apps. Trailing-slash routes, `api/v1` prefix (Principle I parity).

## 1. `GET /api/v1/go/note/<guid>/` — browser redirect to note page (public)

Opens the note's web page from an Anki-known GUID.

- **Auth**: none (public).
- **Path param**: `guid` — the note's stable Anki GUID.
- **Success**: `302 Found`, `Location: {FRONTEND_BASE_URL}/decks/{deck_id}/notes/{note_id}`.
- **Not found**: `404` with `{"detail": "Nota não encontrada."}` (add-on shows "nota não encontrada no Revizza").
- **Notes**: resolves via shared `note_by_guid(guid)`; only non-deleted notes resolve.

## 2. `GET /api/v1/go/note/<guid>/history/` — browser redirect to suggestion history (public)

- **Auth**: none (public).
- **Success**: `302 Found`, `Location: {FRONTEND_BASE_URL}/decks/{deck_id}/suggestions?note_id={note_id}`.
- **Not found**: `404` as above.

## 3. `GET /api/v1/notes/resolve/?guid=<guid>` — JSON resolution (for the add-on suggest flow)

- **Auth**: required (add-on session). Used before submitting a from-Anki suggestion.
- **Query param**: `guid` (required).
- **200**:
  ```json
  {
    "note_id": "0d7f…-uuid",
    "deck_id": "9a1c…-uuid",
    "web_url": "https://app…/decks/{deck_id}/notes/{note_id}",
    "history_url": "https://app…/decks/{deck_id}/suggestions?note_id={note_id}"
  }
  ```
- **400**: `{"guid": ["Parâmetro obrigatório."]}` when `guid` missing.
- **404**: `{"detail": "Nota não encontrada."}`.

## 4. Relaxed reads (existing endpoints, auth downgraded to read-only public)

| Endpoint | Before | After |
|----------|--------|-------|
| `GET /api/v1/notes/{id}/` (`NoteDetailView`) | auth + subscription | **AllowAny** (read-only) |
| `GET /api/v1/decks/{id}/suggestions/` (`DeckSuggestionListView`) | auth + subscription | **AllowAny** (read-only) |

- Only the `GET` read path is public. `POST`/`PATCH`/vote/comment/accept/reject on suggestions keep their existing auth + subscription + moderator gates.
- The suggestions list continues to honour existing filters, including `?note_id=` (used by the history deep-link).

## 5. `POST /api/v1/notes/<note_id>/suggestions/change/` — unchanged, reused by the add-on

The add-on submits here after resolving the GUID. Contract identical to the web flow: body `{fields, tags, category, justification}`; server-side HTML sanitisation, `is_noop` rejection, `@suggestion_ratelimit`, moderation pipeline. Requires auth + subscription. A `401` signals expired session (add-on prompts re-login, preserves draft).

## Settings

- `FRONTEND_BASE_URL` — new env-driven Django setting; base of the redirect `Location`. No trailing slash.
