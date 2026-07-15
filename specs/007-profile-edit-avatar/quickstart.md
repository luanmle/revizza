# Quickstart: Edição de Perfil (Foto e Dados Adicionais)

Validation scenarios proving the feature works end-to-end. Assumes an already-running local dev
stack (`backend/` Django dev server + Supabase project configured per existing `.env`, `frontend/`
Next.js dev server) — see each subtree's own README/AGENTS.md for baseline setup.

## Prerequisites

1. Backend migrations applied (`python manage.py migrate`) after this feature's migration for
   `User.avatar_path` is added.
2. Avatars bucket provisioned: `python manage.py provision_avatars_bucket` (new command, mirrors
   `provision_media_bucket`).
3. A logged-in test user (existing `/accounts/register/` + login flow).

## Scenario 1 — Upload a valid avatar (US1, FR-001/FR-002/FR-004/FR-005)

1. `GET /accounts/me/` → confirm `avatar_url: null`.
2. `PATCH /accounts/me/` with `multipart/form-data`, `avatar=<a real JPEG/PNG under 5MB>`.
3. Expect `200 OK`, `avatar_url` now populated with a reachable public URL.
4. Open the URL directly in a browser → the uploaded image renders.
5. On the frontend, load `/account` → the same avatar renders in the profile header.

## Scenario 2 — Reject invalid upload (US1, FR-003)

1. `PATCH /accounts/me/` with `avatar=<a .txt file renamed to .jpg>` (fails Pillow decode).
2. Expect `400 Bad Request`, `avatar_url` unchanged from before the attempt (re-check via
   `GET /accounts/me/`).
3. Repeat with an oversized file (>5MB) and an oversized-dimension image (>4096px) → same
   rejection behavior, distinct error messages.

## Scenario 3 — Avatar appears at authorship surfaces (US2)

1. As the user from Scenario 1, submit a suggestion on any deck.
2. `GET` the suggestions list for that deck → the suggestion's author entry includes the same
   `avatar_url`.
3. Post a comment on a note/suggestion discussion thread → `GET` the thread → comment's author
   entry includes `avatar_url`.
4. Have the user (or another user with no avatar) be added as a deck moderator → `GET
   /catalog/decks/<id>/moderators/` → confirm the avatar user shows `avatar_url` populated and the
   no-avatar user shows `avatar_url: null` (frontend renders placeholder for the latter).

## Scenario 4 — Edit target_career / target_board (US3, FR-007/FR-008/FR-009)

1. `PATCH /accounts/me/` with `{"target_career": "policial", "target_board": "TJ-SP"}`.
2. Expect `200 OK`, response reflects both new values.
3. On the frontend `/account` page, reload → dropdown shows "policial" selected, text field shows
   "TJ-SP".

## Scenario 5 — No regression on name-only edit (FR-010/SC-005)

1. `PATCH /accounts/me/` with `{"name": "Novo Nome"}` only (no avatar, no career fields in body).
2. Expect `200 OK`, only `name` changes; `avatar_url`/`target_career`/`target_board` remain exactly
   as they were before this request.

## Scenario 6 — Remove avatar (FR-011)

1. As the user from Scenario 1 (has an avatar), `PATCH /accounts/me/` with `{"avatar": null}`.
2. Expect `200 OK`, `avatar_url` now `null`.
3. Reload `/account` → placeholder avatar renders.
