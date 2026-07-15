---

description: "Task list for Edição de Perfil (Foto e Dados Adicionais)"
---

# Tasks: Edição de Perfil (Foto e Dados Adicionais)

**Input**: Design documents from `/specs/007-profile-edit-avatar/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/accounts-api.md, quickstart.md

**Tests**: Included — this repo's existing convention (`backend/tests/{contract,unit,integration}/`)
writes a contract test per endpoint and a unit test per management command/validation helper;
this feature follows that convention, not an opt-in.

**Organization**: Tasks are grouped by user story (US1 avatar upload, US2 avatar on authorship
surfaces, US3 target_career/target_board editing) per spec.md priorities.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps task to US1/US2/US3
- File paths are exact, repo-relative

## Path Conventions

Existing web-app split: `backend/apps/<app>/...`, `backend/tests/{contract,unit,integration}/`,
`frontend/src/...`.

---

## Phase 1: Setup

**Purpose**: Storage bucket provisioning shared by all stories

- [X] T001 Create `backend/apps/sync/management/commands/provision_avatars_bucket.py`, mirroring
      `backend/apps/sync/management/commands/provision_media_bucket.py` but for a **public**
      bucket named `avatars` (`options={"public": True}`); idempotent create/fix-if-private, no
      `--verify` signed-URL round-trip needed since avatar objects are public (uploaded via
      Django, not client-signed URLs).
- [X] T002 [P] Add `backend/tests/unit/test_avatars_bucket.py`, mirroring
      `backend/tests/unit/test_media_bucket.py`'s three cases (creates when missing, no-op when
      already public, flips private→public) for the new command.

**Checkpoint**: `avatars` bucket provisioning verified in isolation before any model/API work.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared model field, storage helper, and serializer plumbing every user story depends on

**⚠️ CRITICAL**: No user story task may start until this phase is complete

- [X] T003 Add `avatar_path = models.CharField(max_length=500, null=True, blank=True)` to `User` in
      `backend/apps/accounts/models.py` (data-model.md).
- [X] T004 Generate migration `backend/apps/accounts/migrations/0004_user_avatar_path.py` for T003
      (`python manage.py makemigrations accounts`).
- [X] T005 Create `backend/apps/accounts/avatars.py`: `validate_and_decode(uploaded_file)` (Pillow
      decode, format allowlist JPEG/PNG/WebP, ≤5MB, ≤4096×4096 — raises a `ValidationError` with a
      human-readable message per data-model.md rule 1-3), `upload(user_id, validated_bytes, ext)
      -> storage_path` (uploads to the `avatars` bucket via a `_storage()` client analogous to
      `apps/sync/media.py`, path `f"{user_id}/{content_hash}.{ext}"`), `delete(storage_path)`,
      `public_url(storage_path) -> str`.
- [X] T006 [P] Add `backend/tests/unit/test_avatars.py`: unit tests for `validate_and_decode`
      (rejects non-image bytes, rejects oversized file, rejects oversized dimensions, accepts a
      valid small JPEG/PNG) using in-memory fixture images (Pillow-generated in the test, no
      binary fixtures committed).
- [X] T007 Add `avatar_url` `SerializerMethodField` to `UserSerializer` in
      `backend/apps/accounts/serializers.py` (returns `avatars.public_url(obj.avatar_path)` if set,
      else `None`); add `"avatar_url"` to `PROFILE_FIELDS`.

**Checkpoint**: Model, migration, validation/storage helper, and the profile's own `avatar_url`
field all exist and are unit-tested. User stories can now proceed.

---

## Phase 3: User Story 1 - Upload de foto de perfil (Priority: P1) 🎯 MVP

**Goal**: Authenticated user uploads/replaces/removes an avatar image via `/account`, with real
server-side validation and no impact on the existing name-edit flow.

**Independent Test**: Log in, open `/account`, upload a valid image → it renders on the profile;
retry with an invalid file → rejected with a clear error, prior avatar untouched (quickstart.md
Scenarios 1, 2, 5, 6).

### Tests for User Story 1

- [X] T008 [P] [US1] Add avatar cases to `backend/tests/contract/test_accounts_me.py`: PATCH with
      valid multipart image → `200`, `avatar_url` populated and fetchable; PATCH with a non-image
      file renamed `.jpg` → `400`, `avatar_url` unchanged; PATCH with oversized file → `400`;
      PATCH `{"name": "Novo Nome"}` only → `avatar_url`/`target_career`/`target_board` unchanged
      (FR-010 no-regression, quickstart Scenario 5); PATCH `{"avatar": null}` on a user with an
      avatar → `200`, `avatar_url` becomes `null` (quickstart Scenario 6).

### Implementation for User Story 1

- [X] T009 [US1] Extend `ProfileUpdateSerializer` in `backend/apps/accounts/serializers.py` to
      accept an optional `avatar` field (image upload, nullable) alongside `name` — depends on T005.
- [X] T010 [US1] Update `MeView.patch` in `backend/apps/accounts/views.py`: when `request.FILES`
      contains `avatar`, call `avatars.validate_and_decode` then `avatars.upload`; on validation
      failure return `400` with the field error and leave `avatar_path` untouched; on success,
      delete the previous storage object (if `avatar_path` was already set and differs) via
      `avatars.delete`, then save the new `avatar_path`; when `request.data.get("avatar")` is
      explicitly `null` (JSON body, no file), delete the existing storage object and clear
      `avatar_path` (FR-011) — depends on T005, T009.
- [X] T011 [US1] Update `Profile` interface and the avatar upload/remove control in
      `frontend/src/app/account/page.tsx`: file input + preview + "remover" action, calling
      `PATCH /accounts/me/` with `multipart/form-data` for upload and `{"avatar": null}` for
      removal, invalidating the `["me"]` query on success, surfacing the `400` error message
      inline — depends on T007, T010.
- [ ] T012 [US1] Run `ui-ux-pro-max` → `impeccable` pipeline (Constitution Principle VII) on the
      updated `/account` avatar control; confirm no horizontal scroll at 360px viewport (FR-053).

**Checkpoint**: User Story 1 fully functional and independently testable/demoable.

---

## Phase 4: User Story 2 - Avatar visível nos pontos de autoria (Priority: P2)

**Goal**: Avatar (or a default placeholder) renders next to the author's name in the suggestion
list, comment threads, and the deck moderator list.

**Independent Test**: With a user who has an avatar (US1) and one who doesn't, view a suggestion
they authored, a comment they posted, and (for a moderator) the deck's moderator list — avatar or
placeholder shows in all three (quickstart.md Scenario 3).

### Tests for User Story 2

- [X] T013 [P] [US2] Add `avatar_url` assertion to the suggestion contract test in
      `backend/tests/contract/test_suggestions_change.py` (or the relevant existing suggestions
      list/detail contract test): author entry includes `avatar_url`, `null` for an author with no
      avatar.
- [X] T014 [P] [US2] Add `avatar_url` assertion to the comments contract test (existing
      `apps.discussions` contract test file, e.g. `backend/tests/contract/test_reports.py`'s
      sibling comment test or a new `test_discussions_comments.py` if none currently asserts the
      comment list shape): `CommentSerializer` output includes `avatar_url`.
- [X] T015 [P] [US2] Add `name`/`avatar_url` assertions to the moderator-list contract test
      (existing `apps.catalog` contract test covering `DeckModeratorListCreateView`, e.g.
      `backend/tests/contract/test_catalog_update.py` or a dedicated moderators test): response
      includes `name` (previously absent) and `avatar_url`, `null` for a moderator with no avatar.

### Implementation for User Story 2

- [X] T016 [P] [US2] Add `avatar_url` `SerializerMethodField` (via `suggestion.author`) to the
      suggestion serializer in `backend/apps/suggestions/serializers.py`, alongside the existing
      `author_name` — depends on T005 (`avatars.public_url`).
- [X] T017 [P] [US2] Add `avatar_url` `SerializerMethodField` (via `comment.author`) to
      `CommentSerializer` in `backend/apps/discussions/serializers.py`, alongside `author_name` —
      depends on T005.
- [X] T018 [P] [US2] Add `name` (`source="user.name"`) and `avatar_url`
      `SerializerMethodField` (via `moderator.user`) to `DeckModeratorSerializer` in
      `backend/apps/catalog/serializers.py` — depends on T005.
- [X] T019 [US2] Create a shared `AvatarBadge`/`UserAvatar` display component in
      `frontend/src/components/user-avatar.tsx` (renders `avatar_url` image or falls back to a
      default placeholder/initials) — depends on T007.
- [X] T020 [US2] Wire the shared avatar component into the suggestion list UI (author entry) —
      depends on T016, T019.
- [X] T021 [US2] Wire the shared avatar component into the comment thread UI (author entry) —
      depends on T017, T019.
- [X] T022 [US2] Wire the shared avatar component into the deck moderator list UI — depends on
      T018, T019.
- [ ] T023 [US2] Run `ui-ux-pro-max` → `impeccable` pipeline on the three updated read surfaces;
      confirm 360px viewport compliance (FR-053) and a graceful no-avatar placeholder (Edge Case).

**Checkpoint**: User Stories 1 AND 2 both independently functional.

---

## Phase 5: User Story 3 - Editar carreira-alvo e banca (Priority: P3)

**Goal**: User edits `target_career` (dropdown of existing 4 choices) and `target_board` (free
text) from `/account`, reflected immediately, with no coupling to catalog filtering.

**Independent Test**: Change `target_career` from "fiscal" to "policial" and edit `target_board`,
save, and see both reflected on `/account` without touching avatar/name (quickstart.md Scenario 4).

### Tests for User Story 3

- [X] T024 [P] [US3] Add cases to `backend/tests/contract/test_accounts_me.py`: PATCH
      `{"target_career": "policial", "target_board": "TJ-SP"}` → `200`, both values reflected on
      a subsequent `GET /accounts/me/`; PATCH with an invalid `target_career` value → `400`.

### Implementation for User Story 3

- [X] T025 [US3] Extend `ProfileUpdateSerializer.Meta.fields` in
      `backend/apps/accounts/serializers.py` to include `target_career` and `target_board`
      (relies on the model's existing `TargetCareer.choices` validation — no new validation code).
- [X] T026 [US3] Add a `target_career` `<select>` (4 existing choices) and a `target_board` text
      input to the form in `frontend/src/app/account/page.tsx`, wired to the same
      `updateProfile` mutation pattern already used for `name` — depends on T025.
- [ ] T027 [US3] Run `ui-ux-pro-max` → `impeccable` pipeline on the extended `/account` form
      fields; confirm 360px viewport compliance (FR-053).

**Checkpoint**: All three user stories independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end confidence once all three stories are complete

- [ ] T028 Run `quickstart.md` Scenarios 1-6 end-to-end against a local dev stack (migrations
      applied, `provision_avatars_bucket` run) and confirm each passes.
- [X] T029 [P] Confirm no regression in existing `backend/tests/contract/test_accounts_me.py` /
      `test_accounts_register.py` / `test_account_privacy.py` suites (full `pytest backend/tests`
      run).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001) only insofar as `avatars.py` references the
  same bucket name; otherwise independent — BLOCKS all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational (T003-T007). No dependency on US2/US3.
- **User Story 2 (Phase 4)**: Depends on Foundational (T005, T007 for the shared avatar
  helper/pattern). Independently testable using a user who already has an avatar via US1, but does
  not require US1's UI code — only the `avatar_path`/`avatars.py` foundation.
- **User Story 3 (Phase 5)**: Depends on Foundational (T003 model field already includes
  `target_career`/`target_board`, which predate this feature) only. Fully independent of US1/US2.
- **Polish (Phase 6)**: Depends on all three user stories being complete.

### Parallel Opportunities

- T001/T002 in parallel (different files).
- T006 in parallel with T007 (different files, both depend only on T005/T003).
- Within US2: T013/T014/T015 (tests) in parallel; T016/T017/T018 (serializers, three different
  apps) in parallel.
- US1, US2, US3 implementation phases can be staffed in parallel once Phase 2 is complete, since
  none of the three shares a mutated file with another (US1 touches `MeView.patch` and the avatar
  upload UI; US2 touches suggestions/discussions/catalog serializers and read-surface UI; US3
  touches `ProfileUpdateSerializer` fields list and the form UI) — only T009/T010 (US1) and T025
  (US3) both touch `ProfileUpdateSerializer`/`MeView`-adjacent files and should be sequenced or
  merged carefully if worked on by different people simultaneously.

---

## Parallel Example: User Story 2

```bash
# Contract tests, three different files:
Task: "Add avatar_url assertion to suggestions contract test"
Task: "Add avatar_url assertion to discussions contract test"
Task: "Add name/avatar_url assertions to moderator-list contract test"

# Serializer changes, three different apps:
Task: "Add avatar_url to suggestion serializer in apps/suggestions/serializers.py"
Task: "Add avatar_url to CommentSerializer in apps/discussions/serializers.py"
Task: "Add name+avatar_url to DeckModeratorSerializer in apps/catalog/serializers.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1).
2. **STOP and VALIDATE**: quickstart.md Scenarios 1, 2, 5, 6 pass; upload/reject/no-regression/
   remove all work end-to-end.
3. Demo: user can upload a profile photo from `/account`.

### Incremental Delivery

1. Setup + Foundational → foundation ready.
2. US1 (avatar upload) → validate independently → demo.
3. US2 (avatar on authorship surfaces) → validate independently → demo.
4. US3 (target_career/target_board editing) → validate independently → demo.
5. Polish → full quickstart + full test suite.
