---
description: "Task list for Add-on Note Actions & Sync Stability"
---

# Tasks: Add-on Note Actions & Sync Stability

**Input**: Design documents from `/specs/010-addon-note-actions/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/note-resolve.md, contracts/addon-actions.md, quickstart.md

**Tests**: Test tasks are INCLUDED — the spec explicitly requests the sync-stability suite (FR-014) and the constitution (Principle VIII) requires automated tests asserting a sync payload update does not alter local study metadata.

**Organization**: Tasks grouped by user story so each ships as an independent increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable — different file, no dependency on an incomplete task
- **[Story]**: User story from spec.md (US1–US4)
- Every task includes an exact file path

## Path Conventions

Three subtrees: `backend/` (Django + DRF), `frontend/` (Next.js), `addon/ankihub_br/` (Anki add-on). Paths below are repo-root relative.

---

## Phase 1: Setup

**Purpose**: Confirm targets and shared config before edits.

- [X] T001 Review both contracts before coding: specs/010-addon-note-actions/contracts/note-resolve.md and specs/010-addon-note-actions/contracts/addon-actions.md
- [X] T002 [P] Re-verify Anki hook signatures against installed stubs (editor_did_init_buttons, editor_did_load_note, reviewer_did_show_question, reviewer_did_show_answer, webview_did_receive_js_message) in addon/.venv/lib/python3.12/site-packages/aqt before use (Principle VI)
- [X] T003 Add FRONTEND_BASE_URL (env-driven, no trailing slash) to backend/config/settings.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared GUID-resolution and visibility helpers used by all three actions.

**⚠️ CRITICAL**: No user story work begins until this phase completes.

- [X] T004 Add shared resolver helper `note_by_guid(guid) -> Note | 404` (non-deleted only) in backend/apps/notes/views.py
- [X] T005 [P] Add reverse-lookup helper `deck_id_for_guid(guid) -> str | None` (query SyncStateCache by note_id==guid) in addon/ankihub_br/db/models.py
- [X] T006 [P] Scaffold add-on GUI modules and register hooks: create addon/ankihub_br/gui/reviewer.py and addon/ankihub_br/gui/editor.py, wire their `setup()` registrations into addon/ankihub_br/gui/__init__.py `setup()`

**Checkpoint**: Resolver + visibility helpers ready. User stories can start.

---

## Phase 3: User Story 1 - Open a note on Revizza from Anki (Priority: P1) 🎯 MVP

**Goal**: A "Ver no Revizza" bottom-bar button opens the current note's public web page.

**Independent Test**: Review a card from a synced deck, click "Ver no Revizza", confirm the browser lands on that exact note's page.

- [X] T007 [US1] Add `GuidRedirectView` (302 → `{FRONTEND_BASE_URL}/decks/{deck_id}/notes/{note_id}` on hit; unknown guid → 302 to `{FRONTEND_BASE_URL}/nota-nao-encontrada` so the browser lands on the Next.js not-found page, US1 AS#3 — no raw JSON) in backend/apps/notes/views.py. Note: the JSON `NoteResolveView` (T014) keeps its `{"detail":...}` 404; only the browser-facing `/go/` views redirect to the friendly page.
- [X] T008 [US1] Add route `go/note/<guid>/` in backend/apps/notes/urls.py
- [X] T009 [US1] Relax `NoteDetailView` GET to AllowAny read-only (drop `_require_subscription` on read only) in backend/apps/notes/views.py
- [X] T010 [P] [US1] Render frontend note page read-only for anonymous visitors (no login redirect) in frontend/src/app/decks/[id]/notes/[noteId]/page.tsx
- [X] T011 [US1] Inject "Ver no Revizza" bottom-bar button on reviewer_did_show_question/reviewer_did_show_answer, gated by `deck_id_for_guid`, `pycmd('revizza:view')` routed via webview_did_receive_js_message → `openLink({API}/go/note/{guid}/)` in addon/ankihub_br/gui/reviewer.py
- [X] T012 [P] [US1] Backend test: redirect resolves valid guid → 302 to the note page; unknown guid → 302 to `/nota-nao-encontrada` (not JSON 404) in backend/apps/notes/tests/test_guid_redirect.py
- [X] T013 [P] [US1] Add-on test: button injected only when guid in cache; hidden otherwise (visibility rule) in addon/tests/test_reviewer_actions.py

**Checkpoint**: US1 delivers a working navigation MVP on its own.

---

## Phase 4: User Story 2 - Suggest a card change directly from Anki (Priority: P2)

**Goal**: Editor button submits the open note's edits as a change suggestion through the existing pipeline, with an offline "nada a sugerir" pre-check.

**Independent Test**: Edit a synced note's field in the editor, submit, confirm it appears on the web Community Suggestions with the edited content/category/justification.

- [X] T014 [US2] Add `NoteResolveView` (`GET /notes/resolve/?guid=`, auth required) + `NoteResolveSerializer` (note_id, deck_id, web_url, history_url) in backend/apps/notes/views.py and backend/apps/notes/serializers.py
- [X] T015 [US2] Add route `notes/resolve/` in backend/apps/notes/urls.py
- [X] T016 [US2] Add `field_hash` nullable column to SyncStateCache plus defensive additive migration in `init_db` in addon/ankihub_br/db/models.py
- [X] T017 [US2] Compute and store the note field-content hash (Note Content only) when applying notes in addon/ankihub_br/main/sync.py, passing it through `record_synced_notes`
- [X] T018 [P] [US2] Add client methods `resolve_note(guid)` and `submit_change_suggestion(note_id, fields, tags, category, justification)` in addon/ankihub_br/ankihub_br_client.py
- [X] T019 [US2] Add editor "Sugerir mudança" button (editor_did_init_buttons; toggle enabled on editor_did_load_note via `deck_id_for_guid`) in addon/ankihub_br/gui/editor.py
- [X] T020 [US2] Implement offline pre-check (hash current fields vs stored field_hash → "Nada a sugerir" and stop) plus the category+justification dialog in addon/ankihub_br/gui/editor.py
- [X] T021 [US2] Implement submit flow off the Qt thread (resolve → POST change suggestion; 201 confirm toast; 400 is_noop → "Nada a sugerir"; 401 → prompt login and preserve draft; other errors → plain message, draft preserved) in addon/ankihub_br/gui/editor.py
- [X] T022 [P] [US2] Backend test: `/notes/resolve/` returns ids/urls for valid guid, 400 on missing guid, 404 on unknown in backend/apps/notes/tests/test_note_resolve.py
- [X] T023 [P] [US2] Add-on test: pre-check returns "no change" when hash equals baseline, opens dialog when it differs in addon/tests/test_editor_suggest.py
- [X] T024 [US2] Add-on test: submit flow paths (mock 201/400/401/network error) preserve draft and surface the right message in addon/tests/test_editor_suggest.py

**Checkpoint**: US2 works independently on top of Foundational.

---

## Phase 5: User Story 4 - Sync remains stable under adverse conditions (Priority: P2)

**Goal**: Automated stability suite proving idempotency, interrupt convergence, edge-case handling, full-resync fallback, and scheduling immutability.

**Independent Test**: Run the suite; every scenario passes and card-state fixtures are byte-identical before/after.

- [X] T025 [P] [US4] Stability tests — idempotency (repeat delta with no changes → zero mutations) and interrupt/resume (partial delta then re-sync → converges, no duplicate/orphan guids) in addon/tests/test_sync_stability.py
- [X] T026 [P] [US4] Stability tests — content edge cases (empty / very large / special-character fields) and subdeck move apply cleanly in addon/tests/test_sync_stability.py
- [X] T027 [US4] Stability test — note-type structural change triggers the full-resync fallback path (not a partial apply) in addon/tests/test_sync_stability.py
- [X] T028 [US4] **Principle VIII gate** — capture a card-state fixture (ease/interval/due/revlog) and assert it is byte-identical before and after applying any sync payload, including the full-resync path, in addon/tests/test_sync_stability.py
- [X] T029 [P] [US4] Stability test — remote edit to a protected field/tag leaves the local protected value untouched (Principle II) in addon/tests/test_sync_stability.py

**Checkpoint**: US4 is self-contained (tests only); can run any time after Foundational.

---

## Phase 6: User Story 3 - View a card's suggestion history from Anki (Priority: P3)

**Goal**: "Ver histórico" bottom-bar button opens the note-filtered suggestions view.

**Independent Test**: For a note with suggestions, click "Ver histórico", confirm the browser opens the suggestions view filtered to that note.

- [X] T030 [US3] Add `GuidHistoryRedirectView` (302 → `{FRONTEND_BASE_URL}/decks/{deck_id}/suggestions?note_id={note_id}` on hit; unknown guid → 302 to the same `/nota-nao-encontrada` friendly page as T007) in backend/apps/notes/views.py
- [X] T031 [US3] Add route `go/note/<guid>/history/` in backend/apps/notes/urls.py
- [X] T032 [US3] Relax `DeckSuggestionListView` GET to AllowAny read-only (writes/votes/comments stay gated) in backend/apps/suggestions/views.py
- [X] T033 [P] [US3] Initialize the suggestions note_id filter from the `?note_id=` search param (empty state, not error, when none) in frontend/src/app/decks/[id]/suggestions/page.tsx
- [X] T034 [US3] Add "Ver histórico" bottom-bar button, `pycmd('revizza:history')` → `openLink({API}/go/note/{guid}/history/)` in addon/ankihub_br/gui/reviewer.py
- [X] T035 [P] [US3] Backend test: history redirect resolves guid → 302 with note_id query; unknown guid → 302 to `/nota-nao-encontrada` in backend/apps/notes/tests/test_guid_redirect.py
- [X] T036 [P] [US3] Frontend test: suggestions page pre-filters from `?note_id=` and shows empty state for a note with no suggestions in frontend/src/app/decks/[id]/suggestions/__tests__/note-filter.test.tsx

**Checkpoint**: US3 reuses the US1 injection + resolver; ships last.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T037 Run full suites: `cd backend && pytest apps/notes/tests apps/suggestions/tests -q`; `cd addon && pytest tests -q`; frontend vitest + lint — all green
- [X] T038 [P] Run `/ponytail-review` on the diff (Principle VI) and address findings
- [X] T039 [P] Run the impeccable gate on the anonymous read-only note page and the URL-filtered suggestions page (WCAG AA, 360px, no generic AI styling — Principle VII)
- [ ] T040 Execute the pre-release manual stability matrix against a real Anki profile per specs/010-addon-note-actions/quickstart.md (FR-014a) and record results

---

## Dependencies & Execution Order

- **Setup (Phase 1)** → **Foundational (Phase 2)** blocks everything.
- **US1 (P1)** — MVP; depends only on Foundational.
- **US2 (P2)** — depends on Foundational (resolver/visibility, field_hash from sync). Independent of US1/US3.
- **US4 (P2)** — tests only; depends on Foundational, independent of US1/US2/US3.
- **US3 (P3)** — reuses US1's reviewer injection module (T011) and the resolver; do after US1.
- **Polish (Phase 7)** — after the stories being shipped are done.

Story order by priority: US1 → US2 → US4 → US3.

## Parallel Opportunities

- Phase 2: T005 and T006 run parallel to T004 (different subtrees).
- US1: T010 (frontend) ∥ T012/T013 (tests) ∥ T011 (add-on) once backend T007–T009 exist.
- US2: T018 (client) ∥ T022 (backend test); T023 ∥ T024 after T019–T021.
- US4: T025, T026, T029 parallel (independent test cases in the same file — coordinate to avoid write conflicts, or split fixtures).
- US3: T033 (frontend) ∥ T035/T036 (tests) ∥ T034 (add-on) once backend T030–T032 exist.
- Cross-story: US2 and US4 can proceed in parallel with US1 (different files/subtrees), since only US3 depends on US1.

## Implementation Strategy

- **MVP**: Phases 1–3 (US1) — the navigation bridge; demoable alone.
- **Increment 2**: US2 (contribution loop) — highest user value after the bridge.
- **Increment 3**: US4 (stability suite) — hardens the sync everything rides on; run in CI.
- **Increment 4**: US3 (history deep-link) — reuses US1 plumbing, ships last.

## Independent Test Criteria

- **US1**: click "Ver no Revizza" on a synced card → browser opens that note's page; absent on non-Revizza cards.
- **US2**: edit a field, submit from editor → suggestion visible on web Community Suggestions; no-op edit → "Nada a sugerir".
- **US3**: click "Ver histórico" → suggestions view filtered to the note; empty state, not error, when none.
- **US4**: stability suite passes every scenario; card-state fixtures byte-identical before/after sync.
