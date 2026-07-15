---

description: "Task list for 006-pending-sync-signal"
---

# Tasks: Sinalização de Sincronização Pendente (indicador + onboarding)

**Input**: Design documents from `/specs/006-pending-sync-signal/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/pending-sync.md, quickstart.md

**Tests**: Included — contract tests for the two extended serializers and the `last_synced_at` write
path match this repo's existing `backend/tests/contract/` convention, plus one add-on unit test for
the pure menu-label function, matching `addon/tests/unit/test_menu.py`'s existing convention.

**Organization**: Tasks are grouped by user story (US1/US2/US3 from spec.md).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Web app (Django backend + Next.js frontend) + Anki add-on. Backend paths relative to `backend/`,
frontend paths relative to `frontend/`, add-on paths relative to `addon/`:
- `apps/catalog/{models,serializers,services}.py` (existing app, `services.py` new)
- `apps/sync/views.py` (existing, extend)
- `tests/contract/test_catalog_list.py`, `tests/contract/test_sync_delta.py`,
  `tests/contract/test_sync_full.py` (existing, extend)
- `src/app/decks/[id]/page.tsx` (existing, extend)
- `ankihub_br/gui/__init__.py` (existing, extend)
- `tests/unit/test_menu.py` (existing, extend)

---

## Phase 1: Setup

**Purpose**: Add the one new column every user story's derived state depends on.

- [ ] T001 Add `last_synced_at = models.DateTimeField(null=True, blank=True)` to `Subscription` in
      `backend/apps/catalog/models.py` (data-model.md).
- [ ] T002 Generate migration: `python manage.py makemigrations catalog` in `backend/`, review the
      generated file in `backend/apps/catalog/migrations/` (no backfill needed — `None` correctly
      means "never synced" for every existing row).

**Checkpoint**: Column exists, no behavior wired yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Write path for `last_synced_at`, the Principle VIII payload-fidelity regression guard,
and the single shared derived-state helper every user story's read-side depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T003 In `backend/apps/sync/views.py::_SubscriberSyncView.get`, set
      `Subscription.objects.filter(user=request.user, deck=deck).update(last_synced_at=timezone.now())`
      under the same success condition already used for the `Notification` `sync_pending` resolution
      (`not status.is_client_error(response.status_code)` and `full_resync_required is not True`) —
      unconditional write, independent of whether a `sync_pending` notification existed to resolve
      (research.md Decision 2, data-model.md).
- [ ] T004 [P] Contract test: successful delta sync sets `Subscription.last_synced_at` for that user
      + deck, in `backend/tests/contract/test_sync_delta.py::test_delta_sync_sets_last_synced_at`.
- [ ] T005 [P] Contract test: successful full sync sets `Subscription.last_synced_at`, in
      `backend/tests/contract/test_sync_full.py::test_full_sync_sets_last_synced_at`.
- [ ] T006 [P] Contract test: a `full_resync_required: true` delta redirect does NOT set
      `last_synced_at` (client hasn't received content yet, mirrors the existing `sync_pending`
      non-resolution regression test), in
      `backend/tests/contract/test_sync_delta.py::test_structural_change_delta_does_not_set_last_synced_at`.
- [ ] T007 [P] Contract test (Constitution Principle VIII regression guard): the `DeltaView`/
      `FullView` response body is byte-for-byte unchanged aside from the new `last_synced_at`
      side-effect — no `Note`/`NoteType`/`Card`/scheduling field is read, filtered, or altered by
      T003 — extending both
      `backend/tests/contract/test_sync_delta.py::test_last_synced_at_write_does_not_alter_sync_payload`
      and
      `backend/tests/contract/test_sync_full.py::test_last_synced_at_write_does_not_alter_sync_payload`
      (mirrors feature 005's `test_notification_resolution_does_not_alter_sync_payload`).
- [ ] T008 Create `deck_sync_state(user, deck) -> Literal["not_synced_yet", "up_to_date",
      "out_of_date"] | None` in `backend/apps/catalog/services.py`: implements the full derived-state
      table from data-model.md as the single shared computation — `None` when not subscribed; else
      `"not_synced_yet"` when `subscription.last_synced_at is None`; else `"out_of_date"` when an
      active `Notification.Type.SYNC_PENDING` row exists for `(user, deck)`; else `"up_to_date"`.
      This is the one place FR-007's "no divergent logic between clients" is enforced — both
      `DeckDetailSerializer.sync_status` (US1/US2) and `DeckSubscribedSerializer.pending_sync` (US3)
      call this same function rather than each re-deriving the state.

**Checkpoint**: `last_synced_at` is written correctly on every successful sync, the sync payload is
provably unaffected, and one shared helper computes the derived state — user stories now only need to
expose/render it.

---

## Phase 3: User Story 1 - Assinante recém-inscrito é guiado até o primeiro sync (Priority: P1) 🎯 MVP

**Goal**: A subscriber who has never synced a deck sees an "ainda não sincronizado" state with a
guided next step on the deck detail page, which clears once they complete their first sync.

**Independent Test**: Subscribe a fresh user to a deck, `GET /api/v1/decks/{id}/` and confirm
`sync_status: "not_synced_yet"`; run a successful sync; `GET` again and confirm `sync_status:
"up_to_date"` (quickstart.md Scenario 1).

### Tests for User Story 1

- [ ] T009 [P] [US1] Contract test: subscribed, `last_synced_at` still `None` → `sync_status ==
      "not_synced_yet"`, in
      `backend/tests/contract/test_catalog_list.py::test_sync_status_not_synced_yet_before_first_sync`.
- [ ] T010 [P] [US1] Contract test: not subscribed → `sync_status is None` (no indicator, no data
      leak), in
      `backend/tests/contract/test_catalog_list.py::test_sync_status_null_when_not_subscribed`.
- [ ] T011 [P] [US1] Contract test: subscribed, synced once, no accepted changes since → `sync_status
      == "up_to_date"`, in
      `backend/tests/contract/test_catalog_list.py::test_sync_status_up_to_date_after_first_sync`.

### Implementation for User Story 1

- [ ] T012 [US1] Add `sync_status` `SerializerMethodField` to `DeckDetailSerializer` in
      `backend/apps/catalog/serializers.py` that calls `deck_sync_state(request.user, deck)` (T008)
      and returns its value directly — no state logic duplicated in the serializer.
- [ ] T013 [US1] Render the `sync_status === "not_synced_yet"` state on
      `frontend/src/app/decks/[id]/page.tsx`: an `Alert` with the "ainda não sincronizado" message and
      the next steps (instalar/configurar o add-on, autenticar, sincronizar), reusing the existing
      `Alert`/`Card` primitives already imported on that page.
- [ ] T014 [US1] Run the `impeccable` audit pass on the new onboarding state in
      `frontend/src/app/decks/[id]/page.tsx` (Constitution VII gate) and address findings.

**Checkpoint**: User Story 1 fully functional and testable independently — new subscribers see the
onboarding state and it clears after their first sync.

---

## Phase 4: User Story 2 - Assinante antigo sabe que o deck tem mudanças novas (Priority: P2)

**Goal**: A subscriber who already completed a sync sees a distinct "desatualizado" state when new
changes are accepted after their last sync, and it clears again on their next sync.

**Independent Test**: With an already-synced subscriber, accept a new suggestion in that deck,
`GET /api/v1/decks/{id}/` and confirm `sync_status: "out_of_date"` (distinct from
`"not_synced_yet"`); sync again and confirm it returns to `"up_to_date"` (quickstart.md Scenario 2).

### Tests for User Story 2

- [ ] T015 [P] [US2] Contract test: subscribed + previously synced, then a suggestion is accepted in
      that deck → `sync_status == "out_of_date"`, in
      `backend/tests/contract/test_catalog_list.py::test_sync_status_out_of_date_after_accept`.
- [ ] T016 [P] [US2] Contract test: from the `out_of_date` state, subscriber syncs again →
      `sync_status` returns to `"up_to_date"`, in
      `backend/tests/contract/test_catalog_list.py::test_sync_status_resolves_to_up_to_date_after_resync`.

### Implementation for User Story 2

- [ ] T017 [US2] Render the `sync_status === "out_of_date"` state on
      `frontend/src/app/decks/[id]/page.tsx`: a visually distinct "desatualizado" message (different
      copy and, per `impeccable` guidance, different visual weight than the onboarding `Alert` from
      US1) — no new backend logic needed, `deck_sync_state`/`sync_status` already covers this value
      (T008/T012).
- [ ] T018 [US2] Extend the `impeccable` audit pass to the out-of-date state in
      `frontend/src/app/decks/[id]/page.tsx` (Constitution VII gate) and address findings.

**Checkpoint**: User Stories 1 AND 2 both work independently — the deck detail page now distinguishes
first-time onboarding from recurring out-of-date, sourced from the same helper.

---

## Phase 5: User Story 3 - Usuário do add-on vê de relance quais decks têm pendência (Priority: P3)

**Goal**: The add-on's "Decks inscritos" menu shows which subscribed decks have pending changes,
without the user opening each deck individually.

**Independent Test**: With 2+ subscribed decks and a pending change in only one, open "Decks
inscritos" in the add-on and confirm only that deck is marked; sync it and confirm the mark clears
(quickstart.md Scenario 3).

### Tests for User Story 3

- [ ] T019 [P] [US3] Contract test: `GET /api/v1/decks/?subscribed=1` exposes `pending_sync: true`
      only for the deck in the `out_of_date` derived state, `false` for others, in
      `backend/tests/contract/test_catalog_list.py::test_subscribed_list_exposes_pending_sync`.
- [ ] T020 [P] [US3] Contract test: a deck with an accepted change but never synced by this subscriber
      (`not_synced_yet`) reports `pending_sync: false` (no false badge before the first sync — spec
      edge case), in
      `backend/tests/contract/test_catalog_list.py::test_subscribed_list_no_pending_sync_before_first_sync`.
- [ ] T021 [P] [US3] Unit test: `menu_item_states` accepts a pending-decks count and appends it to the
      "Decks inscritos" label (e.g. `"Decks inscritos (2)"`), unchanged when count is 0, in
      `addon/tests/unit/test_menu.py::test_menu_item_states_shows_pending_count`.

### Implementation for User Story 3

- [ ] T022 [US3] Add `pending_sync` `SerializerMethodField` to `DeckSubscribedSerializer` in
      `backend/apps/catalog/serializers.py`: `True` only when
      `deck_sync_state(request.user, deck) == "out_of_date"` (T008) — same shared helper as
      `sync_status`, no re-derivation.
- [ ] T023 [US3] Extend `menu_item_states(logged_in: bool, pending_count: int = 0)` in
      `addon/ankihub_br/gui/__init__.py`: append `f" ({pending_count})"` to the "Decks inscritos"
      label when `pending_count > 0`, unchanged otherwise.
- [ ] T024 [US3] Wire `_refresh_menu` in `addon/ankihub_br/gui/__init__.py` to compute
      `pending_count` from the already-fetched `client.get_subscribed_decks()` result's
      `pending_sync` field before calling `menu_item_states`, and pass it through (menu already
      re-fetches on `aboutToShow` via `show_subscribed_decks`'s existing network call — reuse that
      payload, no second request).

**Checkpoint**: All 3 user stories independently functional — web and add-on now share one pending-
sync signal end to end, computed by a single helper.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation across all three surfaces.

- [ ] T025 Run quickstart.md Scenarios 1-4 end to end against a local server + local Anki profile to
      confirm the full loop (onboarding state, out-of-date state, add-on badge, no false positives).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories (every derived state read
  depends on `last_synced_at` being written correctly, on the payload-fidelity guarantee holding, and
  on `deck_sync_state()` existing).
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion, specifically on T008
  (`deck_sync_state`).
  - US1 and US2 both extend `DeckDetailSerializer.sync_status` (US1 creates it in T012, US2 only adds
    a new test case + frontend copy against the same field) — sequence T012 before T015/T017 if
    working sequentially.
  - US3 touches a different serializer (`DeckSubscribedSerializer`) and a different codebase
    (add-on) — no file conflicts with US1/US2, can proceed in parallel once T008 lands.
- **Polish (Phase 6)**: Depends on all 3 user stories being complete (quickstart validates the full
  loop across all three surfaces).

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (needs T008) — no dependency on US2/US3. Implements the
  `sync_status` field itself (T012), which US2 reuses read-only.
- **US2 (P2)**: Can start after Foundational, but its test tasks (T015/T016) assume `sync_status`
  (T012) already exists — sequence after US1's T012, or coordinate if working in parallel on the same
  file.
- **US3 (P3)**: Can start after Foundational (needs T008) — independent of US1/US2 (different
  serializer, different codebase).

### Within Each User Story

- Tests before implementation (tests must fail first).
- Story complete before moving to next priority.

### Parallel Opportunities

- T004, T005, T006, T007 (foundational tests, different files) in parallel; T008 (shared helper)
  should land before any of T012/T022 start, but can be written in parallel with T004-T007.
- T009, T010, T011 (US1 tests, same file, independent fixtures) in parallel.
- T015, T016 (US2 tests, same file, independent fixtures) in parallel.
- T019, T020, T021 (US3 tests, two different files) in parallel.
- US3 (T019-T024) can proceed in parallel with US1/US2 once Foundational is done — different
  serializer, different codebase (add-on vs. web).

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "Contract test: sync_status not_synced_yet before first sync in backend/tests/contract/test_catalog_list.py"
Task: "Contract test: sync_status null when not subscribed in backend/tests/contract/test_catalog_list.py"
Task: "Contract test: sync_status up_to_date after first sync in backend/tests/contract/test_catalog_list.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`last_synced_at` column)
2. Complete Phase 2: Foundational (write path, payload-fidelity guard, shared `deck_sync_state`
   helper)
3. Complete Phase 3: User Story 1 (`sync_status` field + onboarding UI)
4. **STOP and VALIDATE**: quickstart.md Scenario 1
5. Deploy/demo if ready — this alone closes the biggest funnel drop (subscribed but never reached the
   add-on)

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → onboarding state on deck detail → test independently → demo (MVP)
3. US2 → recurring out-of-date state → test independently → demo
4. US3 → add-on menu badge → test independently → demo
5. Polish → full quickstart run across web + add-on

---

## Notes

- [P] tasks = different files, or independent test functions in the same file with independent
  fixtures — this repo's existing convention (see feature 005's `test_notifications.py`) allows
  marking same-file independent contract tests as [P].
- [Story] label maps task to specific user story for traceability.
- `deck_sync_state()` (T008) is the single source of truth behind both `sync_status` (US1/US2) and
  `pending_sync` (US3) — FR-007's "no divergent logic between clients" is enforced by construction,
  not by convention.
- Verify tests fail before implementing.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
