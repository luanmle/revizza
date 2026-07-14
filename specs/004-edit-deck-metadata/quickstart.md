# Quickstart: Validate deck metadata editing

## Prerequisites

- Backend running locally (`backend/`, existing `manage.py runserver` setup) with a test deck already
  published (via the existing publish flow or fixture) and at least two users: one active moderator,
  one plain subscriber.
- Migration applied: `python manage.py migrate catalog` (adds `anki_deck_name`, backfilled from `name`).

## Scenario 1 — moderator edits successfully (US1)

1. Authenticate as the active moderator of deck `X`.
2. `PATCH /api/v1/decks/X/` with `{"description": "<b>Nova descrição</b>"}`.
3. Expect `200 OK`; response `description` contains the sanitized HTML.
4. `GET /api/v1/decks/X/` (any user) → confirm the new description is returned.
5. `GET /api/v1/decks/` (catalog list, any user) → confirm the new description/title appears there too.

See [contracts/decks-update.md](./contracts/decks-update.md) for the full request/response shape.

## Scenario 2 — non-moderator blocked (US2)

1. Authenticate as the plain subscriber (not a moderator of deck `X`).
2. `PATCH /api/v1/decks/X/` with any field → expect `403 Forbidden`.
3. Repeat as a moderator whose `DeckModerator.status == pending` → expect `403 Forbidden`.
4. `GET /api/v1/decks/X/` → confirm the deck's fields are unchanged from before the attempt.

## Scenario 3 — sync payload unaffected by rename (FR-006 / research.md Decision 4)

1. Note the deck's `anki_deck_name` in the DB (or via the sync full payload's `deck_name` field)
   before any edit.
2. As the active moderator, `PATCH /api/v1/decks/X/` with `{"name": "Novo Título"}` → `200 OK`.
3. `GET /api/v1/decks/X/sync/full/` (as the subscribed add-on would) → confirm `deck_name` in the
   payload is unchanged from step 1, even though the catalog `name` is now "Novo Título".

## Scenario 4 — validation

1. As the active moderator, `PATCH /api/v1/decks/X/` with `{"name": ""}` → expect `400 Bad Request`,
   no fields changed.
2. `PATCH /api/v1/decks/X/` with `{"subject_tags": ["direito", "direito", ""]}` → expect `200 OK` with
   `subject_tags` normalized to `["direito"]` (dedup, drop blank).

## Expected outcome

All four scenarios pass → SC-001, SC-002, SC-003 in [spec.md](./spec.md) are satisfied.
