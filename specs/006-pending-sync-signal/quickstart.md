# Quickstart: Sinalização de Sincronização Pendente

Prerequisites: local backend running (`cd backend && python manage.py runserver`), a test user, a
deck with an active moderator, and (for US3) the Anki add-on pointed at the local backend.

## Scenario 1 — Onboarding (US1)

1. Subscribe the test user to a deck that has never been synced by them:
   `POST /api/v1/decks/{id}/subscriptions/`.
2. `GET /api/v1/decks/{id}/` → expect `sync_status: "not_synced_yet"`.
3. Open `/decks/{id}` in the web app → expect the "ainda não sincronizado" onboarding message with
   next steps (install/configure add-on, sync).
4. Run a successful delta or full sync as that user for that deck
   (`GET /api/v1/decks/{id}/sync/delta/` or `.../full/`).
5. `GET /api/v1/decks/{id}/` again → expect `sync_status: "up_to_date"`.

## Scenario 2 — Recurring out-of-date (US2)

1. With the same user/deck now `up_to_date` from Scenario 1, accept a new suggestion in that deck
   (moderator decides via `SuggestionAcceptView`).
2. `GET /api/v1/decks/{id}/` as the subscriber → expect `sync_status: "out_of_date"` (distinct from
   `not_synced_yet`).
3. Open `/decks/{id}` in the web app → expect the "desatualizado" message (not the onboarding one).
4. Sync again → expect `sync_status` back to `"up_to_date"`.

## Scenario 3 — Add-on indicator (US3)

1. With at least one subscribed deck in `out_of_date` state (from Scenario 2) and one in
   `up_to_date`, call `GET /api/v1/decks/?subscribed=1` as the add-on client (or open "Decks
   inscritos" in Anki) → expect `pending_sync: true` only on the out-of-date deck's entry.
2. Sync that deck via the add-on → reopen "Decks inscritos" → expect `pending_sync: false` for that
   deck.

## Scenario 4 — No false positives (SC-004)

1. Subscribe to a fresh deck, sync immediately (no changes yet accepted) → `sync_status:
   "up_to_date"`, `pending_sync: false`. Confirms a same-day subscribe+sync never shows a spurious
   pending indicator.
