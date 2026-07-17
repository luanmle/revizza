---

description: "Task list for feature 011: Hardened Add-on Media Sync"

---

# Tasks: Hardened Add-on Media Sync

**Input**: Design documents from `/specs/011-addon-media-sync/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/media-sync.md, quickstart.md

**Tests**: Included — spec.md's Test Plan Notes and Success Criteria (SC-001..SC-007) require automated coverage, and constitution Principle VIII mandates a scheduling-immutability test for any plan touching sync endpoints/note data models.

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P1/P1/P2/P2) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1..US5)

## Path Conventions

Web app + add-on (per plan.md Project Structure): `backend/apps/...`, `backend/tests/...`, `addon/ankihub_br/...`, `addon/tests/...`.

---

## Phase 1: Setup

**Purpose**: Data-model and routing scaffolding needed before any real logic lands.

- [X] T001 Add `status` field (`pending_upload`/`ready`, default `ready`) to `MediaFile` in `backend/apps/notes/models.py`; generate migration `backend/apps/notes/migrations/0003_mediafile_status.py` that backfills existing rows to `ready` (data-model.md)
- [X] T002 [P] Register `decks/<uuid:deck_id>/media/<str:content_hash>/confirm/` route in `backend/apps/sync/urls.py` (view implemented in T004; contracts/media-sync.md §4)
- [X] T003 [P] Add `MEDIA_MAX_BYTES = 10 * 1024 * 1024` constant and a `user_files/media_staging/` path helper in `addon/ankihub_br/main/media.py` (research.md §3)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The core validate → stage → write mechanism and backend status-gating that every P1 user story (US1, US2, US3) depends on for correctness.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Implement `MediaUploadConfirmView` (POST, creator/moderator auth, idempotent 200 on already-`ready`, rate-limited via `RATELIMIT_PUBLISH_RATE` per contracts §4) in `backend/apps/sync/views.py`, wired to T002's route — contracts/media-sync.md §4 (depends on T001)
- [X] T005 Gate `MediaDownloadView.get` on `MediaFile.status == "ready"` (return 404 `{"detail": "Mídia ainda não disponível."}` for `pending_upload`) in `backend/apps/sync/views.py` — contracts/media-sync.md §2 (depends on T001)
- [X] T006 Filter `_deck_payload`'s `media` list to `status="ready"` only in `backend/apps/sync/views.py` — contracts/media-sync.md §1 (depends on T001)
- [X] T007 [P] Extend `backend/tests/contract/test_sync_media.py`: `pending_upload` hash → 404 from `GET /media/{hash}/`; `POST /decks/{id}/media/{hash}/confirm/` flips status and is idempotent on repeat; delta/full responses never list a `pending_upload` hash (depends on T004, T005, T006)
- [X] T008 Switch `AnkiHubBrClient.download_file` to a streamed GET through `self.session` (not a bare `requests.get`) with `Content-Length` pre-check and running-byte-count abort at `MEDIA_MAX_BYTES` in `addon/ankihub_br/ankihub_br_client/client.py` — research.md §5, §6
- [X] T009 [P] Add `AnkiHubBrClient.confirm_media_upload(deck_id: str, content_hash: str) -> None` in `addon/ankihub_br/ankihub_br_client/client.py` — contracts/media-sync.md §5
- [X] T010 Implement `stage_media(col, media_items, client, staging_dir) -> list[StagedMedia]` in `addon/ankihub_br/main/media.py`: for each item, derive the deterministic `<content_hash>.<ext>` resolved filename first, and skip the download entirely if `col.media.have(resolved_filename)` is already true (primary skip condition — the file was already committed in a prior run, per FR-008/FR-013); otherwise skip only the re-download (reusing the staged bytes) if a matching validated file is still present in `staging_dir` from a prior not-yet-committed run; otherwise stream-download via T008, validate SHA-256 against manifest `content_hash` and size ≤ `MEDIA_MAX_BYTES`, and write to the `tempfile`-based staging location — research.md §2, §3, data-model.md "Staged media" (resolves `/speckit-analyze` finding F2)
- [X] T011 Implement `commit_media(col, staged_items) -> dict[str, str]` in `addon/ankihub_br/main/media.py`: for each staged item, write via `col.media.write_data(resolved_filename, data)` (never `Path.write_bytes()`), delete the temp file once committed, return a `content_hash → final_filename` map — research.md §1 (depends on T010)
- [X] T012 Implement a stale-staging-file sweep at the start of `stage_media` (delete files in `staging_dir` older than a TTL comfortably longer than one sync run) in `addon/ankihub_br/main/media.py` — research.md §3, spec Edge Cases (depends on T010)
- [X] T013 Rewrite `<img src="...">` references in note field values using the `content_hash → final_filename` map from T011, applied inside `_fill_fields`/`_apply_notes` before `col.update_note`/`col.add_note`, in `addon/ankihub_br/main/sync.py` — FR-011 (depends on T011)
- [X] T014 Reorder `perform_sync` in `addon/ankihub_br/main/sync.py`: call `stage_media` (T010) before `apply_delta`/`apply_full`, thread the resulting *partial* `content_hash → filename` map (items that failed validation are simply absent from it, never raised as an exception) into note application (T013) so a note whose image failed still commits with that one `<img src>` reference left unresolved rather than aborting the deck, then call `commit_media` (T011) within the same collection-write phase — `main/backup.py`'s existing restore-on-exception stays reserved for genuine collection-mutation errors, not media validation misses. Per research.md §9 (resolves `/speckit-analyze` finding F1), the sync cursor still advances normally since the note itself committed; the unresolved reference is naturally retried on a later sync once `stage_media`'s `col.media.have()` check (T010) still reports it missing — FR-012, FR-013 (depends on T010, T011, T013)
- [X] T015 Make `publish_initial_deck` resumable in `addon/ankihub_br/main/publish.py`: skip re-uploading any hash the backend already reports as an existing `MediaFile`, and call `confirm_media_upload` (T009) immediately after each individual successful `upload_signed_media` — FR-004, FR-006 (depends on T009)
- [X] T016 [P] Add the Constitution Principle VIII + SC-007 test: assert a card's scheduling fields (`due`, `ivl`, `factor`, `reps`, `queue`) are byte-identical before and after a media-bearing `apply_delta`/`apply_full` run, AND assert every field value/tag other than the note's `<img src>` attribute is also unchanged (diff full field-value/tag state, excluding only the documented rewrite), in `addon/tests/unit/test_media_sync.py` — contracts/media-sync.md "Constitution Principle VIII test obligation", spec.md SC-007 (depends on T013, T014)

**Checkpoint**: Foundation ready — validate/stage/write/status-gate/confirm mechanism exists end-to-end; all P1 user stories can now be exercised.

---

## Phase 3: User Story 1 - A note with an image syncs correctly to a new Anki profile (Priority: P1) 🎯 MVP

**Goal**: A subscriber's first (or delta) sync installs referenced images correctly and they render on the card.

**Independent Test**: Publish a deck with an `<img>`-referencing note, subscribe from a second empty profile, sync, confirm the image file exists locally and the card renders it.

### Tests for User Story 1

- [X] T017 [US1] Integration test: publish a deck with one image-bearing note, sync to a fresh profile, assert `<content_hash>.<ext>` exists in `collection.media/` and the note field references it, in `addon/tests/unit/test_media_sync.py`
- [X] T018 [US1] Integration test: delta sync adding a new image to an already-synced deck downloads only the new file; pre-existing media untouched, in `addon/tests/unit/test_media_sync.py`
- [X] T019 [US1] Integration test: a note referencing content already present locally (same hash, arrived via another deck) is reused without re-downloading — assert the mocked client's download call count is zero for that hash (SC-004), in `addon/tests/unit/test_media_sync.py`
- [X] T020 [US1] Backend contract test: publish issues `media_upload_urls` only for new hashes; after confirm, the same deck's delta/full response includes that hash in `media`, in `backend/tests/contract/test_sync_media.py`

**Checkpoint**: User Story 1 fully functional and independently testable (happy-path end-to-end).

---

## Phase 4: User Story 2 - Two decks with same-named, different-content media don't clobber each other (Priority: P1)

**Goal**: Same-named files from different decks never overwrite each other locally.

**Independent Test**: Publish two decks each with a same-named, different-content file; subscribe to both from one profile; sync; verify each note shows its own distinct image.

### Tests for User Story 2

- [X] T021 [P] [US2] Test: two decks publish same-named different-content files; subscriber syncing both ends up with two distinct local files, each note referencing its own, in `addon/tests/unit/test_media_sync.py`
- [X] T022 [US2] Test: re-syncing the same two decks after the initial collision resolves reuses the previously resolved hash-derived filenames — no renaming churn, and the mocked client's download call count is zero on the repeat run (SC-004), in `addon/tests/unit/test_media_sync.py`

**Checkpoint**: User Story 2 independently testable — collision-freedom verified.

---

## Phase 5: User Story 3 - Invalid or incomplete media is rejected without corrupting the collection (Priority: P1)

**Goal**: Bad transfers (wrong hash, oversized, truncated, unsafe filename) never reach the media folder or collection database.

**Independent Test**: Simulate a download whose bytes don't match the manifest hash (or are oversized/truncated) and confirm the collection is unchanged and no file lands under its final name.

### Tests for User Story 3

[P] [US3] Test: SHA-256 mismatch → file discarded, never written, item reported failed, in `addon/tests/unit/test_media_sync.py`
[P] [US3] Test: body exceeding 10 MB (both via `Content-Length` and via streamed running count) → transfer aborted before full buffering, item reported failed, in `addon/tests/unit/test_media_sync.py`
[P] [US3] Test: truncated/interrupted stream → no partial file ever reachable under its final resolved name, in `addon/tests/unit/test_media_sync.py`
[P] [US3] Test: a server-supplied filename containing `../`, absolute paths, or drive letters is never used as a filesystem path — write path only ever goes through `col.media.write_data`, in `addon/tests/unit/test_media_sync.py`
[US3] Test: collection and media folder are unchanged (no corruption) after each of T023-T026's rejection cases, in `addon/tests/unit/test_media_sync.py`

**Checkpoint**: User Story 3 independently testable — integrity guarantees verified.

---

## Phase 6: User Story 4 - Publishing and syncing large image sets keeps Anki responsive (Priority: P2)

**Goal**: Anki's UI stays responsive during media-heavy publish/sync, with progress and clean cancellation.

**Independent Test**: Publish/sync a deck with a large image set and confirm the Anki window stays interactive throughout, with visible progress.

### Implementation for User Story 4

- [X] T028 [US4] Wrap `sync_all`'s network/staging phase in `QueryOp(...).without_collection().run_in_background()`, chained into a second `QueryOp` for the collection-apply phase (`stage_media` → `apply_delta`/`apply_full` + `commit_media`), in `addon/ankihub_br/gui/__init__.py` — research.md §4 (depends on Phase 2)
- [X] T029 [P] [US4] Wrap `publish_initial_deck`'s upload+confirm loop in `QueryOp(...).without_collection()` in `addon/ankihub_br/gui/__init__.py` — research.md §4 (depends on T015)
- [X] T030 [US4] Add a configurable concurrency limit (default 4, per research.md §10) for parallel media downloads inside `stage_media` in `addon/ankihub_br/main/media.py` — FR-019 (depends on T010)
- [X] T031 [US4] Surface visible progress (count/percentage) for the staging phase via the `QueryOp` progress callback in `addon/ankihub_br/gui/__init__.py` — FR-020 (depends on T028)
- [X] T032 [US4] Add clean cancellation: an in-progress media staging run discards its in-flight temp writes, already-committed items are kept, in `addon/ankihub_br/main/media.py` and `addon/ankihub_br/gui/__init__.py` — FR-021 (depends on T028, T030)

### Manual Validation for User Story 4

- [ ] T033 [US4] Run quickstart.md §6 (responsiveness scenario) on a real Anki profile with a throttled connection and a 10+ file, near-10MB image batch; record result in `specs/011-addon-media-sync/quickstart.md`

**Checkpoint**: User Story 4 independently testable — responsiveness verified.

---

## Phase 7: User Story 5 - Interrupted sync can be safely retried (Priority: P2)

**Goal**: A sync interrupted mid-batch resumes cleanly on retry — no re-download of already-valid media, no premature cursor advance.

**Independent Test**: Kill the process after some but not all media in a delta succeed, then re-sync and confirm completion with no duplicate downloads.

### Tests for User Story 5

- [X] T034 [P] [US5] Test: a run where some media validate and one fails still commits all notes (per research.md §9) — the deck's `last_synced_mod` cursor advances normally, but the note referencing the failed hash keeps its unresolved `<img src>` and is not marked as if that image succeeded, in `addon/tests/unit/test_media_sync.py` (depends on T014)
- [X] T035 [US5] Test: retrying the same delta after a partial failure does not re-download or re-validate media already committed to `collection.media` or still staged from the prior run (T010's `col.media.have()`/staging-cache checks) — assert the mocked client's download call count only covers the previously-missing hash (SC-004), in `addon/tests/unit/test_media_sync.py` (depends on T010, T012)
- [X] T036 [P] [US5] Test: a stale staging file from a simulated crash (older than the sweep TTL) is removed at the start of the next sync run, in `addon/tests/unit/test_media_sync.py` (depends on T012)
- [X] T037 [US5] Test: retrying `publish_initial_deck` after a prior attempt partially uploaded media does not create duplicate `MediaFile` rows and only uploads/confirms the still-unconfirmed hashes, in `addon/tests/unit/test_media_publish.py` (depends on T015)

**Checkpoint**: User Story 5 independently testable — resumability verified.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T038 [P] Run `/ponytail-review` on the full diff per constitution Principle VI
- [X] T039 Run `cd backend && uv run pytest` and `cd addon && uv run pytest`; fix any regressions surfaced across both suites
- [ ] T040 [P] Execute quickstart.md §1-§5 end-to-end and record actual results in `specs/011-addon-media-sync/quickstart.md`
- [X] T041 [P] Cross-reference `specs/001-ankihub-brasil-mvp/contracts/sync.md`'s media rows with `contracts/media-sync.md` (add a one-line pointer note in the 001 doc; do not restate the contract)
- [X] T042 [P] Regression test guarding FR-001/FR-002/FR-003 (media identified only via note field scan, hash dedup within one publish payload, no bearer token sent on `upload_signed_media`) still hold after the T010/T011/T015 changes, in `addon/tests/unit/test_media_publish.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001, T002 specifically) — BLOCKS all user stories.
- **User Stories (Phase 3-7)**: All depend on Foundational (Phase 2) completion.
  - US1, US2, US3 (all P1) can proceed in parallel once Foundational is done — none depends on another.
  - US4 depends on Foundational only (not on US1/US2/US3), but is naturally validated after correctness stories exist.
  - US5 depends on Foundational (T010, T012, T014, T015 specifically) — independent of US1-US4.
- **Polish (Phase 8)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependency on US2/US3/US4/US5.
- **US2 (P1)**: No dependency on US1/US3/US4/US5 — exercises the same Foundational hash-naming mechanism from a different angle.
- **US3 (P1)**: No dependency on US1/US2/US4/US5 — exercises the same Foundational validation mechanism from a different angle.
- **US4 (P2)**: No dependency on US1/US2/US3/US5 — purely a threading/UX wrapper around already-correct Foundational logic.
- **US5 (P2)**: No dependency on US1/US2/US3/US4 — exercises Foundational resumability/staging-cache behavior directly.

### Parallel Opportunities

- T002, T003 (Setup) in parallel.
- T007, T009 (Foundational) in parallel with the sequential T004→T005/T006 backend chain and the T008→T009 client chain, respectively (different files).
- T016 in parallel with the start of Phase 3 once its own dependencies (T013, T014) land.
- Once Foundational (Phase 2) is done, US1/US2/US3/US5 test-writing can proceed in parallel (different describe-blocks in shared test files — coordinate on `test_media_sync.py` to avoid merge conflicts, or split further if staffed by multiple people).
- Within US3: T023-T026 in parallel (independent test cases, same file — safe if staffed by one person; split file per-case if parallelized across people).
- Within US5: T034, T036 in parallel.

---

## Parallel Example: Foundational Phase

```bash
# Backend and add-on client tracks are independent files - run together:
Task: "Implement MediaUploadConfirmView in backend/apps/sync/views.py"
Task: "Add AnkiHubBrClient.confirm_media_upload in addon/ankihub_br/ankihub_br_client/client.py"
```

## Parallel Example: User Story 3

```bash
# All four rejection-case tests target the same file but independent scenarios:
Task: "Test SHA-256 mismatch rejection in addon/tests/unit/test_media_sync.py"
Task: "Test oversized-body rejection in addon/tests/unit/test_media_sync.py"
Task: "Test truncated-stream rejection in addon/tests/unit/test_media_sync.py"
Task: "Test path-traversal filename rejection in addon/tests/unit/test_media_sync.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup.
2. Complete Phase 2: Foundational (CRITICAL — this is where nearly all the actual mechanism lives: safe write, hash-naming, staging/validation, status gating, confirm endpoint).
3. Complete Phase 3: User Story 1.
4. **STOP and VALIDATE**: run quickstart.md §3 manually; confirm SC-001.
5. Deploy/demo if ready — a deck with images now publishes and syncs correctly end-to-end.

### Incremental Delivery

1. Setup + Foundational → mechanism exists and is unit-tested at the module level (T007, T016).
2. Add US1 → validate happy path → demo (MVP).
3. Add US2 → validate collision-freedom → demo.
4. Add US3 → validate fault-injection/integrity → demo.
5. Add US4 → validate responsiveness → demo.
6. Add US5 → validate resumability → demo.
7. Polish.

### Why so much lives in Foundational

Unlike a typical CRUD feature, US1/US2/US3 are three *properties* of one shared mechanism (correct happy-path write, collision-free naming, and rejection-of-bad-input are all facets of the same `stage_media`/`commit_media` pipeline), not three separable subsystems — building "just enough for US1" would already require the hash-naming and validation logic that US2/US3 test. Phase 2 exists so each of those three P1 stories can be independently *verified* even though they share one implementation, per the constitution's minimal-code discipline (Principle VI): one mechanism, three test angles, rather than three redundant implementations.

---

## Notes

- [P] tasks = different files or independent test cases, no dependencies.
- [Story] label maps task to specific user story for traceability.
- Commit after each task or logical group.
- Stop at any checkpoint to validate a story independently.
- T014 and T015 are the two places existing behavior changes order (media-before-notes in sync; per-file confirm in publish) — review these diffs carefully against `main/sync.py`'s existing backup/restore and `main/publish.py`'s existing atomic-payload construction before merging.
- T010 and T014 encode the `/speckit-analyze` F1/F2 remediation (research.md §9, §10): a failed media item skips only its own `<img src>` resolution, never the whole deck; already-committed media is detected via `col.media.have()`, not just the staging directory. Read research.md §9-§10 before implementing either task.
