# Phase 0 Research: Add-on Note Actions & Sync Stability

All spec unknowns were resolved during `/speckit-clarify` (see spec.md → Clarifications). This document records the technical decisions that follow from those answers, with Anki API signatures verified against the installed stubs in `addon/.venv/lib/python3.12/site-packages/aqt` (Principle VI).

## 1. GUID → web page resolution (FR-004, FR-005)

- **Decision**: Backend owns resolution. Two public redirect views on the `notes` app:
  - `GET /api/v1/go/note/<guid>/` → `302` to `{FRONTEND_BASE_URL}/decks/{deck_id}/notes/{note_id}`
  - `GET /api/v1/go/note/<guid>/history/` → `302` to `{FRONTEND_BASE_URL}/decks/{deck_id}/suggestions?note_id={note_id}`
  Both share one resolver helper `note_by_guid(guid) -> Note | 404`. The add-on only builds `{API_BASE}/go/note/{guid}[/history]/` and opens it in the default browser; it stores no GUID→URL mapping.
- **Rationale**: Keeps the add-on dumb and the URL scheme stable/server-controlled. A GUID is globally unique in this system (Anki GUIDs are collision-safe); a note lookup by GUID is a single indexed query. `FRONTEND_BASE_URL` is a new backend setting (env-driven, like the other deploy URLs).
- **Alternatives considered**: (a) Add-on caches deck/note ids and builds the frontend URL directly — rejected: duplicates server state locally and breaks if the URL scheme changes. (b) Pre-fill the notes search with the GUID — rejected: lands the user on a list, not the note, and the current search filter accepts only the platform UUID.
- **Edge (FR US1 #3)**: GUID unknown to the platform → resolver returns `404` with a plain message; the add-on catches the non-2xx before opening the browser and shows "nota não encontrada no Revizza".

## 2. Public read-only note & suggestion views (FR-005a)

- **Decision**: Relax exactly two GET endpoints to `AllowAny` **read-only**:
  - `NoteDetailView` (`GET /notes/{id}/`)
  - `DeckSuggestionListView` (`GET /decks/{id}/suggestions/`) — the note-filtered history target
  Drop the `_require_subscription` gate on these reads only; all writes (suggestions, votes, comments) keep their auth + subscription gates unchanged. Frontend note page and suggestions page render read-only when the visitor is unauthenticated.
- **Rationale**: Matches the clarified "public read pages, no login wall". Decks are non-private by design (PRD §2.3 non-goals), so deck content and its community suggestions are already visible to every subscriber — widening to anonymous read exposes no personal-account data. Comment **threads** stay gated (not required by the two navigation actions).
- **Alternatives considered**: Login-wall-then-redirect — rejected per clarification (adds friction). Separate public serializers — rejected (YAGNI; the existing read serializers expose only content already shown to subscribers).
- **LGPD note (Principle III)**: suggestion author display name is already shown to all subscribers; no new field is exposed. Recorded as reviewed in the Constitution Check.

## 3. From-Anki change suggestion (FR-006, FR-007, US2)

- **Decision**: The editor button submits through the **existing** change-suggestion pipeline. Flow: add-on resolves the open note's GUID to its platform id via a small JSON endpoint `GET /api/v1/notes/resolve/?guid=<guid>` (auth required) → then `POST /api/v1/notes/{note_id}/suggestions/change/` with `{fields, tags, category, justification}` (the current contract). No new suggestion type or flag — a from-Anki suggestion is byte-for-byte a web suggestion (Principle II: it is a proposal into moderation, not an upstream content write).
- **Rationale**: Reuses server-side HTML sanitisation, the existing `is_noop` backstop, `@suggestion_ratelimit`, and the moderation/queue path. One extra resolve GET is cheap and keeps the suggestion endpoint unchanged.
- **Alternatives considered**: A parallel GUID-addressed suggestion endpoint (`…/notes/by-guid/<guid>/…`) — rejected: duplicates the whole suggestion view to save one round-trip. Scraping the redirect `Location` header for the id — rejected: fragile, ties two unrelated endpoints together.
- **Auth (FR-010)**: submission requires a valid add-on session; on `401`/expired token the add-on prompts sign-in and preserves the drafted fields/justification (FR-009).

## 4. Offline "nada a sugerir" pre-check (FR-008)

- **Decision**: Cache a per-note **content snapshot hash** at sync time and compare locally before opening the suggestion dialog. Add a `field_hash` column to `SyncStateCache` (add-on local SQLite in `user_files/`), computed as a stable hash of the note's applied field values at sync. On "Sugerir mudança", hash the current local field values and compare to the stored `field_hash`; equal → show "nada a sugerir" and do not open the form.
- **Rationale**: Works fully offline (no submit-time round-trip, per clarification). The snapshot is **Note Content only** (Principle VIII) — it lives beside the existing sync cache, never touches Card State (`cards`/`revlog`). The server `is_noop` check remains the authoritative backstop.
- **Alternatives considered**: Fetch official at submit — rejected by clarification (network, offline-fails). Store full field text — rejected: a hash is enough for equality and smaller. Rely only on server `is_noop` — rejected: can't show the offline pre-check UX the clarification requires.

## 5. Anki UI integration points (verified hook names)

- **Reviewer bottom-bar buttons ("Ver no Revizza", "Ver histórico")** — inject into the reviewer bottom web on `gui_hooks.reviewer_did_show_question` / `reviewer_did_show_answer` via `mw.reviewer.bottom.web.eval(<js appending buttons>)`; the buttons `pycmd('revizza:view')` / `pycmd('revizza:history')`, routed through `gui_hooks.webview_did_receive_js_message` (namespaced `revizza:` prefix). Buttons appear only when the current note's GUID is in the local sync cache (i.e. it belongs to a subscribed Revizza deck), else omitted/disabled (FR-001).
  - `ponytail:` the reviewer bottom bar has no dedicated "add button" hook; JS eval into `mw.reviewer.bottom.web` is the same injection technique the real AnkiHub add-on uses. Ceiling: if Anki changes bottom-bar markup, the injection selector needs updating — isolate the JS in one string constant.
- **Editor "Sugerir mudança" button** — `gui_hooks.editor_did_init_buttons` adds the toolbar button; `gui_hooks.editor_did_load_note` toggles its enabled state by checking deck membership of the loaded note.
- **Deck membership / reverse lookup** — `SyncStateCache` is keyed by `(deck_id, note_id=guid)`; a query `where note_id == guid` yields the owning Revizza `deck_id`, proving membership and giving the id needed to build history/suggestion URLs. Add helper `deck_id_for_guid(guid) -> str | None`.
- **Opening the browser** — `aqt.utils.openLink(url)` (Qt `QDesktopServices` under the hood), off no thread concern (fire-and-forget).
- **Network off the UI thread** — reuse the existing `_run_network` / `QueryOp(...).without_collection().run_in_background()` pattern already in `gui/__init__.py` for the resolve + submit calls (FR-009).

## 6. Sync stability test suite (FR-014, FR-014a, Principle VIII)

- **Decision**: Two layers.
  - **Automated (CI)** — `addon/tests/test_sync_stability.py` drives `main/sync.py` against a mocked/in-memory collection double, asserting: (a) idempotency — a second delta with no changes mutates nothing; (b) interrupt/resume — applying a partial delta then re-syncing converges with no duplicate/orphan `guid`s; (c) content edge cases — empty/large/special-character fields, subdeck moves; (d) note-type structural change triggers the full-resync fallback path; (e) **scheduling immutability** — a captured "card state" fixture (ease/interval/due/revlog) is byte-identical before and after any sync payload application.
  - **Manual (pre-release)** — a documented matrix in `quickstart.md` run against a real Anki profile for the behaviours the collection double can't faithfully reproduce (real scheduler, real media, real interrupted network).
- **Rationale**: Matches the clarified "both" answer and the existing add-on test style (headless pytest, no live Anki). The scheduling-immutability assertion is the concrete Principle VIII test task the constitution requires of any plan touching sync.
- **Alternatives considered**: Real-profile-only automation — rejected: slow, non-deterministic, not CI-friendly. Mocked-only — rejected: misses real-scheduler/media fidelity the constitution cares about.
