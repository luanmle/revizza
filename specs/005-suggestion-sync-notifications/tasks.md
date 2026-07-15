---

description: "Task list for 005-suggestion-sync-notifications"
---

# Tasks: Notificações de Suggestion/Sync

**Input**: Design documents from `/specs/005-suggestion-sync-notifications/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/notifications.md, quickstart.md

**Tests**: Included — contract tests for the 4 new endpoints and integration tests per trigger point
(decision, creation, sync) match this repo's existing `backend/tests/contract/` convention, and are
the concrete testable behaviors called for by the spec's Acceptance Scenarios / quickstart.md.

**Organization**: Tasks are grouped by user story (US1/US2/US3 from spec.md).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Single project split (Django backend + Next.js frontend). Backend paths relative to `backend/`,
frontend paths relative to `frontend/`:
- `apps/notifications/{models,services,serializers,views,urls}.py` (new app)
- `apps/suggestions/{decisions,views}.py` (existing, extend)
- `apps/sync/views.py` (existing, extend)
- `config/{settings/base,urls}.py` (existing, extend)
- `tests/contract/test_notifications.py` (new)
- `src/lib/notifications.ts` (new), `src/components/SiteHeader.tsx` (existing, extend)

---

## Phase 1: Setup

**Purpose**: Scaffold the new Django app before any model/view work.

- [X] T001 Create app skeleton `backend/apps/notifications/` (`__init__.py`, `apps.py` with
      `AppConfig.name = "apps.notifications"`, empty `models.py`, `migrations/__init__.py`, `tests/__init__.py`).
- [X] T002 Register `"apps.notifications"` in `INSTALLED_APPS` in `backend/config/settings/base.py`
      (after `"apps.suggestions"`, per plan.md Project Structure).

**Checkpoint**: App importable, no models yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The `Notification` model, migration, and URL wiring that every user story's endpoints
and trigger points depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Create `Notification(BaseModel)` in `backend/apps/notifications/models.py` per
      data-model.md: `recipient` FK → `accounts.User` (CASCADE), `type` choices
      (`suggestion_accepted`/`suggestion_rejected`/`new_suggestion`/`sync_pending`), `deck` FK →
      `catalog.Deck` (CASCADE), `suggestion` FK → `suggestions.Suggestion` (CASCADE, null/blank),
      `note` FK → `notes.Note` (CASCADE, null/blank), `read_at` (nullable datetime), `resolved_at`
      (nullable datetime); `Meta.indexes = [("recipient", "read_at", "created_at")]`;
      `Meta.constraints` with the partial `UniqueConstraint` on `(recipient, deck)` filtered to
      `type="sync_pending", resolved_at__isnull=True` (data-model.md).
- [X] T004 Generate migration: `python manage.py makemigrations notifications` in `backend/`, review
      the generated file in `backend/apps/notifications/migrations/`.
- [X] T005 [P] Create `NotificationSerializer` in `backend/apps/notifications/serializers.py` per
      contracts/notifications.md response shape (`id, type, deck_id, deck_name, suggestion_id,
      note_id, rejection_reason, read_at, created_at`), with `rejection_reason` as a
      `SerializerMethodField` returning `obj.suggestion.rejection_reason` only when
      `obj.type == Notification.Type.SUGGESTION_REJECTED`, else `None`.
- [X] T006 Create `backend/apps/notifications/services.py` with `notify_suggestion_decided(suggestion)`
      and `notify_new_suggestion(suggestion)` per research.md Decision 2 and contracts/notifications.md
      trigger-point table (function bodies land in US1/US2 tasks below; this task creates the module
      and empty function signatures with docstrings referencing the FR they satisfy).
- [X] T007 Create `backend/apps/notifications/urls.py` with the 4 routes from
      contracts/notifications.md (`""`, `"unread-count/"`, `"<uuid:pk>/read/"`, `"read-all/"`) and
      include it in `backend/config/urls.py` under `path("api/v1/", include("apps.notifications.urls"))`.

**Checkpoint**: Model, migration, serializer skeleton, and URL wiring exist — user stories can now
implement their views/trigger logic in parallel.

---

## Phase 3: User Story 1 - Autor sabe o resultado da sua sugestão (Priority: P1) 🎯 MVP

**Goal**: Author of a suggestion gets an in-app notification when a moderator accepts or rejects it,
including the rejection reason when applicable.

**Independent Test**: Create a suggestion, decide it (accept and, separately, reject with a reason)
via `SuggestionAcceptView`/`SuggestionRejectView`, and verify the author's `GET
/api/v1/notifications/` includes the corresponding entry (quickstart.md Scenario 1 steps 1-3, Scenario 3).

### Tests for User Story 1

- [X] T008 [P] [US1] Contract test: accept a suggestion, assert author receives a
      `suggestion_accepted` `Notification` row (`type`, `deck`, `suggestion`, `read_at is None`) in
      `backend/tests/contract/test_notifications.py::test_accept_notifies_author`.
- [X] T009 [P] [US1] Contract test: reject a suggestion with `rejection_reason="duplicado"`, assert
      the author's notification serializes `rejection_reason == "duplicado"` and a
      `suggestion_accepted`-type notification is NOT also created, in
      `backend/tests/contract/test_notifications.py::test_reject_notifies_author_with_reason`.
  - Note: reject NOT created is confirmed by asserting exactly one Notification exists for that decision (not two).
- [X] T010 [P] [US1] Contract test: decide a suggestion whose `author_id is None` (author account
      deleted, FK `SET_NULL`), assert no `Notification` is created and the view still returns 200, in
      `backend/tests/contract/test_notifications.py::test_decision_skips_notification_when_author_deleted`.
- [X] T011 [P] [US1] Contract test: `GET /api/v1/notifications/{id}/read/` marks it read; re-posting
      is idempotent (still 204, `read_at` unchanged after first call) in
      `backend/tests/contract/test_notifications.py::test_mark_read_idempotent`.
- [X] T012 [P] [US1] Contract test: `POST /api/v1/notifications/read-all/` marks all of
      `request.user`'s unread notifications read and leaves other users' untouched, in
      `backend/tests/contract/test_notifications.py::test_read_all_scoped_to_user`.

### Implementation for User Story 1

- [X] T013 [US1] Implement `notify_suggestion_decided(suggestion)` body in
      `backend/apps/notifications/services.py`: skip if `suggestion.author_id is None`; else
      resolve `target_notes = list(suggestion.target_notes.all())`, and set
      `note=target_notes[0].note if len(target_notes) == 1 else None` (single-note suggestions
      reference that note; bulk suggestions reference only deck+suggestion per FR-001); then
      `Notification.objects.create(recipient=suggestion.author, type=SUGGESTION_ACCEPTED or
      SUGGESTION_REJECTED based on suggestion.status, deck=suggestion.deck, suggestion=suggestion,
      note=note)` (contracts/notifications.md trigger-point table).
- [X] T014 [US1] Call `notify_suggestion_decided(suggestion)` in
      `backend/apps/suggestions/decisions.py::SuggestionDecisionView.post`, right after
      `suggestion.decided_by = request.user; suggestion.save()`, still inside the existing
      `with transaction.atomic():` block (plan.md Summary / research.md Decision 2).
- [X] T015 [US1] Implement `NotificationListView` (`generics.ListAPIView`,
      `pagination_class = DefaultCursorPagination`, queryset filtered to
      `recipient=request.user`, `select_related("deck", "suggestion", "note")`, optional
      `?unread=true` filter) in `backend/apps/notifications/views.py`.
- [X] T016 [US1] Implement `NotificationMarkReadView` (`POST /{id}/read/`, scoped to
      `recipient=request.user`, sets `read_at=timezone.now()` if still null, 204) in
      `backend/apps/notifications/views.py`.
- [X] T017 [US1] Implement `NotificationReadAllView` (`POST /read-all/`, bulk `.update(read_at=now())`
      on `recipient=request.user, read_at__isnull=True`, 204) in
      `backend/apps/notifications/views.py`.
- [X] T018 [US1] Wire `NotificationListView`/`NotificationMarkReadView`/`NotificationReadAllView`
      into `backend/apps/notifications/urls.py` (routes already stubbed in T007).

**Checkpoint**: User Story 1 fully functional and testable independently — author sees accept/reject
notifications with reason, can mark read.

---

## Phase 4: User Story 2 - Moderador sabe que há sugestão nova para revisar (Priority: P2)

**Goal**: Every active moderator of a deck (except the suggestion's own author) gets notified when a
new suggestion is created in that deck.

**Independent Test**: Create a suggestion in a deck with 1+ active moderators, verify each receives a
`new_suggestion` notification, and verify a moderator who is also the author does not (quickstart.md
Scenario 2).

### Tests for User Story 2

- [X] T019 [P] [US2] Contract test: non-moderator creates a suggestion in a deck with one active
      moderator, assert the moderator receives a `new_suggestion` notification, in
      `backend/tests/contract/test_notifications.py::test_new_suggestion_notifies_moderators`.
- [X] T020 [P] [US2] Contract test: a moderator creates a suggestion in their own deck, assert they do
      NOT receive a `new_suggestion` notification for their own submission, in
      `backend/tests/contract/test_notifications.py::test_new_suggestion_excludes_author_moderator`.
- [X] T021 [P] [US2] Contract test: suggestion created in a deck with zero active moderators, assert
      no `new_suggestion` notifications are created (no error), in
      `backend/tests/contract/test_notifications.py::test_new_suggestion_no_moderators_noop`.

### Implementation for User Story 2

- [X] T022 [US2] Implement `notify_new_suggestion(suggestion)` body in
      `backend/apps/notifications/services.py`:
      `DeckModerator.objects.filter(deck=suggestion.deck, status=DeckModerator.Status.ACTIVE)
      .exclude(user=suggestion.author).values_list("user_id", flat=True)`, then
      `Notification.objects.bulk_create([Notification(recipient_id=uid, type=NEW_SUGGESTION,
      deck=suggestion.deck, suggestion=suggestion) for uid in ...])` (contracts/notifications.md).
- [X] T023 [US2] Call `notify_new_suggestion(suggestion)` in
      `backend/apps/suggestions/views.py` at the 3 creation entrypoints: `_create_change_suggestion`
      (used by both `ChangeSuggestionCreateView` and `BulkChangeSuggestionCreateView`),
      `NewNoteSuggestionCreateView.post`, `DeletionSuggestionCreateView.post` — inside the existing
      `transaction.atomic()` block where one exists, immediately after `Suggestion.objects.create(...)`
      otherwise (plan.md Project Structure).

**Checkpoint**: User Stories 1 AND 2 both work independently — moderators now see new-suggestion
alerts alongside authors seeing decision alerts.

---

## Phase 5: User Story 3 - Assinante sabe que há mudanças aguardando sincronização (Priority: P3)

**Goal**: Subscribers of a deck get a `sync_pending` notification when a suggestion is accepted in
that deck, deduplicated to at most one active per (subscriber, deck), resolved on their next
successful sync.

**Independent Test**: Accept a suggestion in a deck with subscribers, verify each subscriber gets one
`sync_pending` notification; accept a second suggestion before any subscriber syncs, verify still only
one active notification per subscriber; have a subscriber call `/decks/{id}/sync/delta/`, verify their
notification resolves (quickstart.md Scenario 1 steps 4-7).

### Tests for User Story 3

- [X] T024 [P] [US3] Contract test: accept a suggestion in a deck with a subscriber, assert the
      subscriber has one unresolved `sync_pending` notification, in
      `backend/tests/contract/test_notifications.py::test_accept_notifies_subscribers_sync_pending`.
- [X] T025 [P] [US3] Contract test: accept two suggestions in sequence in the same deck before the
      subscriber syncs, assert exactly one active `sync_pending` `Notification` row exists for that
      (recipient, deck) pair (DB constraint + `get_or_create` idempotency), in
      `backend/tests/contract/test_notifications.py::test_sync_pending_deduplicated`.
- [X] T026 [P] [US3] Contract test: subscriber calls `GET /decks/{id}/sync/delta/`, assert their
      active `sync_pending` notification now has `resolved_at` set, in
      `backend/tests/contract/test_notifications.py::test_delta_sync_resolves_pending_notification`.
- [X] T027 [P] [US3] Contract test: subscriber calls `GET /decks/{id}/sync/full/` (not just delta),
      assert `sync_pending` also resolves via `FullView`, in
      `backend/tests/contract/test_notifications.py::test_full_sync_resolves_pending_notification`.
- [X] T028 [P] [US3] Contract test: verify the sync response payload/shape for `DeltaView`/`FullView`
      is byte-for-byte unchanged aside from the added notification side-effect (no Note/Card field
      touched) — Principle VIII regression guard, in
      `backend/tests/contract/test_sync_delta.py::test_notification_resolution_does_not_alter_sync_payload`
      (extend existing sync test file per plan.md Project Structure).
- [X] T028b [P] [US3] Contract test: trigger a structural change (note type `structure_changed_at` >
      `since_mod`) so `DeltaView` returns `full_resync_required: true`, assert the subscriber's active
      `sync_pending` notification is still unresolved after this call (FR-006 — redirect to full
      resync is not sync completion), in
      `backend/tests/contract/test_notifications.py::test_structural_change_delta_does_not_resolve_pending`.

### Implementation for User Story 3

- [X] T029 [US3] Extend `notify_suggestion_decided(suggestion)` in
      `backend/apps/notifications/services.py`: when `suggestion.status == Suggestion.Status.ACCEPTED`,
      for each `Subscription.objects.filter(deck=suggestion.deck).values_list("user_id", flat=True)`,
      `Notification.objects.get_or_create(recipient_id=uid, deck=suggestion.deck,
      type=SYNC_PENDING, resolved_at__isnull=True, defaults={})` (research.md Decision 1 —
      `get_or_create` against the partial unique constraint gives FR-005 idempotency for free).
- [X] T030 [US3] Add notification resolution to `backend/apps/sync/views.py::_SubscriberSyncView.get`:
      after `response = self.sync(request, deck)` returns successfully (i.e. not a 4xx) AND
      `response.data.get("full_resync_required") is not True` (a structural-change delta redirect is
      NOT sync completion — the client hasn't received the content yet, it's about to call `FullView`;
      resolving here would violate FR-006), call `Notification.objects.filter(recipient=request.user,
      deck=deck, type=SYNC_PENDING, resolved_at__isnull=True).update(resolved_at=timezone.now())`
      (research.md Decision 1 — resolve regardless of whether the delta contained *notes*, but not on
      the full-resync-required redirect), then return `response`.

**Checkpoint**: All 3 user stories independently functional — full suggest → moderate → propagate loop
now has in-app notifications end to end.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Retention job, frontend surface, and end-to-end validation.

- [X] T031 [P] Implement `GET /api/v1/notifications/unread-count/`
      (`NotificationUnreadCountView`, `{"count": Notification.objects.filter(recipient=request.user,
      read_at__isnull=True).count()}`) in `backend/apps/notifications/views.py` and wire into
      `backend/apps/notifications/urls.py` (contracts/notifications.md).
- [X] T032 [P] Implement `purge_read_notifications` management command in
      `backend/apps/notifications/management/commands/purge_read_notifications.py`: delete
      `Notification.objects.filter(read_at__lt=timezone.now() - timedelta(days=90))` (FR-010).
- [X] T033 [P] Create `frontend/src/lib/notifications.ts` with `Notification` type
      (matching contracts/notifications.md response shape) and `api.get`/`api.post` wrapper functions
      for the 4 endpoints, reusing `frontend/src/lib/api-client.ts`'s `Paginated<T>` type for the list
      endpoint.
- [X] T034 Add `useUnreadCount()` hook (`useQuery`, `refetchInterval: 45_000`,
      `queryKey: ["notifications", "unread-count"]`) and `NotificationBell` component to
      `frontend/src/components/SiteHeader.tsx` (~line 44-49, next to `ThemeToggle`), rendering a
      badge and a `DropdownMenu` listing recent notifications (fetched on open) with a "marcar todas
      como lidas" action wired to `read-all/` via `useMutation` + `queryClient.invalidateQueries`.
- [X] T035 Run quickstart.md Scenarios 1-4 end to end against a local server to confirm the full loop
      (accept/reject notifies author, new suggestion notifies moderators excluding author-moderator,
      sync resolves pending notification, mark-read/read-all work).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately.
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories (model/migration/URL
  skeleton needed by every story).
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion.
  - US1, US2, US3 touch different functions in `services.py` and different existing view files
    (`decisions.py` vs `views.py` vs `sync/views.py`) — no cross-story file conflicts, can proceed in
    parallel if staffed, or sequentially in priority order (P1 → P2 → P3).
- **Polish (Phase 6)**: Depends on all 3 user stories being complete (unread-count and frontend bell
  read from notifications created by all 3 trigger types; quickstart validates the full loop).

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependency on US2/US3. Also implements the shared
  list/read/read-all endpoints that US2/US3 notifications flow through (they only add new `type`
  values and new creation call sites, not new endpoints).
- **US2 (P2)**: Can start after Foundational — independent of US1's decision-notification logic
  (different service function, different view file).
- **US3 (P3)**: Can start after Foundational — independent of US1/US2, but extends the same
  `notify_suggestion_decided` function US1 created (T013); sequence T013 before T029 if working
  sequentially, or coordinate if parallel (both edit `services.py`, different functions/sections).

### Within Each User Story

- Tests before implementation (tests must fail first).
- Service function body before the view/hook that calls it.
- Story complete before moving to next priority.

### Parallel Opportunities

- T001 (app skeleton) and T002 (INSTALLED_APPS) are sequential (T002 needs T001's app to exist).
- T005 (serializer) can run in parallel with T006 (services skeleton) and T007 (urls) once T003/T004
  (model + migration) land.
- All US1 tests (T008-T012) in parallel; all US2 tests (T019-T021) in parallel; all US3 tests
  (T024-T028) in parallel.
- T031, T032, T033 (unread-count endpoint, management command, frontend lib) are independent files —
  parallel.

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "Contract test: accept notifies author in backend/tests/contract/test_notifications.py"
Task: "Contract test: reject notifies author with reason in backend/tests/contract/test_notifications.py"
Task: "Contract test: decision skips notification when author deleted in backend/tests/contract/test_notifications.py"
Task: "Contract test: mark read idempotent in backend/tests/contract/test_notifications.py"
Task: "Contract test: read-all scoped to user in backend/tests/contract/test_notifications.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (model, migration, urls skeleton)
3. Complete Phase 3: User Story 1 (author decision notifications + list/read/read-all endpoints)
4. **STOP and VALIDATE**: quickstart.md Scenario 1 steps 1-3 and Scenario 3, plus Scenario 4
5. Deploy/demo if ready — this alone closes the loudest silence in the loop (author never knowing the
   outcome of their suggestion)

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 → author notifications + notification center endpoints → test independently → demo (MVP)
3. US2 → moderator new-suggestion alerts → test independently → demo
4. US3 → subscriber sync-pending indicator → test independently → demo
5. Polish → unread-count badge, frontend bell, retention job, full quickstart run

---

## Notes

- [P] tasks = different files or independent sections of `services.py`, no dependencies.
- [Story] label maps task to specific user story for traceability.
- Contract tests all live in one new file (`test_notifications.py`) since they share fixtures
  (deck/moderator/subscriber/author) — this repo's existing convention groups related contract tests
  per feature area (see `test_sync_full.py`, `test_catalog_update.py`).
- Verify tests fail before implementing.
- Commit after each task or logical group.
- Stop at any checkpoint to validate story independently.
