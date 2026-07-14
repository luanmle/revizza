---

description: "Task list for 004-edit-deck-metadata"
---

# Tasks: Edição de título/descrição/tags do deck pelo moderador

**Input**: Design documents from `/specs/004-edit-deck-metadata/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/decks-update.md, quickstart.md

**Tests**: Included — contract tests for the new `PATCH` endpoint and the sync-payload
non-regression check (research.md Decision 4 / FR-006) are concrete testable behaviors, matching
this repo's existing `backend/tests/contract/` convention.

**Organization**: Tasks are grouped by user story (US1/US2/US3 from spec.md).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Single project split (Django backend + Next.js frontend). Backend paths relative to `backend/`,
frontend paths relative to `frontend/`:
- `apps/catalog/models.py`, `apps/catalog/serializers.py`, `apps/catalog/views.py`
- `apps/sync/views.py`
- `tests/contract/test_catalog_update.py` (new), `tests/contract/test_sync_full.py` (existing, extend)
- `src/app/decks/[id]/edit/page.tsx` (new), `src/app/decks/[id]/page.tsx` (existing, extend)

---

## Phase 1: Setup

**Purpose**: Add the immutable sync-facing field before any endpoint uses it.

- [X] T001 Add `anki_deck_name = models.CharField(max_length=200)` to `Deck` in
      `backend/apps/catalog/models.py` (data-model.md), placed next to `name`.
- [X] T002 Generate migration for `anki_deck_name` in `backend/apps/catalog/migrations/`
      (`python manage.py makemigrations catalog`) with a data migration/`RunPython` step (or
      `default=`+`AlterField` two-step) backfilling `anki_deck_name = name` for all existing rows
      (research.md Decision 4 migration note).

**Checkpoint**: Schema change applied and backfilled; safe for all following phases.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Decouple the sync payload from the now-editable `name` BEFORE the edit endpoint ships,
so `name` is never wired to local Anki deck placement even transiently.

**⚠️ CRITICAL**: Must complete before Phase 3 (US1) — otherwise editing `name` would immediately
regress FR-006/Principle II.

- [X] T003 In `backend/apps/sync/views.py`, change `_deck_payload` to read
      `deck.anki_deck_name` instead of `deck.name` for the `deck_name` key (research.md Decision 4).
- [X] T004 In `backend/apps/sync/views.py::PublishView.post`, set
      `anki_deck_name=data["name"]` alongside `name=data["name"]` when creating the `Deck`
      (data-model.md) so newly published decks get the snapshot from day one.
- [X] T005 [P] Extend `backend/tests/contract/test_sync_full.py` (or `test_sync_publish.py`) with a
      regression test: publish a deck, assert `anki_deck_name == name` initially, then directly
      mutate `Deck.name` in the DB and assert `GET /decks/{id}/sync/full/`'s `deck_name` is
      unchanged (still the original `anki_deck_name`) — proves sync is decoupled from `name` even
      before the edit endpoint exists.

**Checkpoint**: Sync payload is now immune to `name` edits — Phase 3 (US1) can safely make `name`
writable.

---

## Phase 3: User Story 1 - Moderador atualiza metadados do deck (Priority: P1) 🎯 MVP

**Goal**: Active moderator can `PATCH` title/description/tags and see the change reflected in the
catalog immediately.

**Independent Test**: Authenticated as active moderator, `PATCH /api/v1/decks/{id}/`, then `GET`
list+detail confirm new values (quickstart.md Scenario 1).

### Tests for User Story 1

- [X] T006 [P] [US1] Contract test: active moderator `PATCH`s `name`+`description`+`subject_tags`,
      gets `200` with updated `DeckDetailSerializer` shape, and a subsequent `GET /decks/{id}/` and
      `GET /decks/` both reflect the new values, in `backend/tests/contract/test_catalog_update.py`
      (new file; contracts/decks-update.md), plus a partial-update case: `PATCH` with only
      `description` leaves `name`/`subject_tags` unchanged (FR-007).
- [X] T007 [P] [US1] Contract test: `PATCH` with `name=""` returns `400`, no fields change (FR-003),
      in `backend/tests/contract/test_catalog_update.py`.
- [X] T008 [P] [US1] Contract test: `PATCH` with `subject_tags=["a","a",""]` returns `200` with
      `subject_tags == ["a"]` (dedup + drop blanks, FR-008), and `PATCH` with
      `subject_tags="not-a-list"` returns `400`, in `backend/tests/contract/test_catalog_update.py`.
- [X] T009 [P] [US1] Contract test: `PATCH` with a `description` containing `<script>` or an inline
      `onerror` handler returns `200` with the dangerous markup stripped (FR-005, reusing the same
      allowlist assertions style as note-field sanitization tests), in
      `backend/tests/contract/test_catalog_update.py`.

### Implementation for User Story 1

- [X] T010 [US1] Add `DeckUpdateSerializer` in `backend/apps/catalog/serializers.py`: fields
      `name`/`description`/`subject_tags`, all optional (`required=False`) for partial updates;
      `validate_name` rejects blank/whitespace-only; `validate_subject_tags` rejects non-list/non-string
      items; `validate_description` runs `apps.notes.sanitize.sanitize_html` (data-model.md,
      research.md Decision 3).
- [X] T011 [US1] In `backend/apps/catalog/views.py`, extend `DeckDetailView` with a `patch` method:
      look up the deck, reuse the active-moderator guard (research.md Decision 2, same pattern as
      `DeckModeratorRemoveView.delete`), validate via `DeckUpdateSerializer(partial=True)`,
      dedupe/normalize `subject_tags` (drop empty/duplicate entries) before saving, save only the
      fields present in the payload, and return `DeckDetailSerializer(deck).data` (contracts/decks-update.md).

**Checkpoint**: User Story 1 fully functional and independently testable — moderators can edit deck
metadata and it's visible catalog-wide.

---

## Phase 4: User Story 2 - Sistema impede edição por quem não é moderador ativo (Priority: P2)

**Goal**: Non-active-moderators (subscribers, pending moderators, anonymous) are blocked from
editing.

**Independent Test**: Authenticated as subscriber or pending moderator, `PATCH` is rejected and no
data changes (quickstart.md Scenario 2).

### Tests for User Story 2

- [X] T012 [P] [US2] Contract test: authenticated non-moderator `PATCH`s a deck → `403`, deck
      unchanged, in `backend/tests/contract/test_catalog_update.py`.
- [X] T013 [P] [US2] Contract test: moderator with `DeckModerator.status == pending` `PATCH`s the
      deck → `403`, deck unchanged, in `backend/tests/contract/test_catalog_update.py`.
- [X] T014 [P] [US2] Contract test: unauthenticated request `PATCH`s the deck → rejected (matching
      this app's existing unauthenticated-request behavior/status code), in
      `backend/tests/contract/test_catalog_update.py`.

### Implementation for User Story 2

- [X] T015 [US2] Verify the active-moderator guard added in T011 already covers all three cases
      above (pending status, non-moderator, unauthenticated) — this is the same guard already used by
      `DeckModeratorRemoveView.delete`; if any case in T012-T014 fails, fix the guard in
      `backend/apps/catalog/views.py`, not by adding a second check path.

**Checkpoint**: User Stories 1 AND 2 both verified — authorized edits work, unauthorized edits are
blocked.

---

## Phase 5: User Story 3 - Potencial assinante vê a descrição atualizada antes de assinar (Priority: P3)

**Goal**: Non-subscribed users see the latest title/description/tags on the deck detail page before
deciding to subscribe.

**Independent Test**: As a non-subscriber, load the deck detail page after a moderator's edit and
confirm it shows the latest data (quickstart.md Scenario 1, step 4; this story adds no new backend
behavior beyond what US1 already returns via `GET`).

### Tests for User Story 3

- [X] T016 [P] [US3] Contract test: after a moderator's `PATCH`, a second (non-subscribed, non-
      moderator) authenticated user's `GET /decks/{id}/` returns the updated
      `name`/`description`/`subject_tags`, in `backend/tests/contract/test_catalog_update.py`.

### Implementation for User Story 3

- [X] T017 [US3] Add a moderator-only "Editar deck" entry point on
      `frontend/src/app/decks/[id]/page.tsx`, gated on `is_moderator` (same field/pattern the page
      already reads for other moderator-only UI), linking to the new edit route.
- [X] T018 [US3] Create `frontend/src/app/decks/[id]/edit/page.tsx`: form for `name`/`description`/
      `subject_tags`, submitting `PATCH /api/v1/decks/{id}/` (contracts/decks-update.md), redirecting
      back to the deck detail page on success and showing the `400`/`403` `detail` message on error.

**Checkpoint**: All three user stories independently functional — this is the full feature.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across all stories.

- [X] T019 Run `quickstart.md` scenarios 1-4 end to end against a local backend (migration applied)
      to confirm SC-001/SC-002/SC-003 hold.
- [X] T020 [P] Re-run `/ponytail-review` (Constitution Principle VI) on the diff to confirm no
      speculative abstraction was introduced (e.g., no new permission class for a single call site,
      per research.md Decision 2).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Phase 1 (needs `anki_deck_name` to exist) — BLOCKS User
  Story 1, because making `name` writable without this decoupling would regress FR-006.
- **User Story 1 (Phase 3)**: Depends on Phase 2.
- **User Story 2 (Phase 4)**: Depends on Phase 3 (reuses the guard added in T011) — verification-only
  phase, adds no new implementation beyond a possible fix to T011's guard.
- **User Story 3 (Phase 5)**: Depends on Phase 3 (needs the `PATCH` endpoint to exist to demo the
  updated data, and needs T011's response shape for the frontend form).
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### Parallel Opportunities

- T005 (Phase 2 regression test) can be written in parallel with T003/T004 (fails until they land).
- T006-T009 (US1 tests) are `[P]` — different test functions in the same new file; write in parallel,
  they must all fail before T010/T011 land.
- T012-T014 (US2 tests) are `[P]` — same file, independent functions.
- T016 (US3 test) is `[P]`, independent of T017/T018 (frontend).
- T017/T018 (frontend) are sequential (T018 is linked from T017) — not parallel.

---

## Parallel Example: User Story 1

```bash
# Launch all US1 contract tests together (must fail before T010/T011 exist):
Task: "Contract test: full metadata update in backend/tests/contract/test_catalog_update.py"
Task: "Contract test: blank name rejected in backend/tests/contract/test_catalog_update.py"
Task: "Contract test: subject_tags normalization/rejection in backend/tests/contract/test_catalog_update.py"
Task: "Contract test: description sanitization in backend/tests/contract/test_catalog_update.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`anki_deck_name` field + migration).
2. Complete Phase 2: Foundational (sync payload decoupled from `name`) — CRITICAL, do not skip.
3. Complete Phase 3: User Story 1 (the `PATCH` endpoint itself).
4. **STOP and VALIDATE**: Run quickstart.md Scenarios 1, 3, 4 against a local backend.
5. Ship — US1 alone already satisfies the reported problem (moderator can edit, catalog reflects it).

### Incremental Delivery

1. Setup + Foundational → schema and sync safety ready.
2. Add User Story 1 → contract-test-verified → deployable (backend-only, no frontend yet).
3. Add User Story 2 → confirms the existing guard is airtight (should require no new code in the
   common case).
4. Add User Story 3 → frontend edit form ships, completing the end-to-end feature.

---

## Notes

- No new Django app, no new dependency, no new DRF permission class (research.md Decisions 1-2) —
  reuse existing `apps/catalog` and `apps/sync`.
- `anki_deck_name` (T001-T002) must land and be wired into `_deck_payload` (T003) **before** the
  `PATCH` endpoint (T011) is exposed, otherwise there is a window where editing `name` would leak into
  sync payloads.
- Verify tests fail before implementing (T006-T009, T012-T014, T016 before T010/T011/T017/T018).
- Commit after each task or logical group.
