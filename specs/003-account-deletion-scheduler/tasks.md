---

description: "Task list for 003-account-deletion-scheduler"
---

# Tasks: Scheduler de Deleção de Contas (LGPD)

**Input**: Design documents from `/specs/003-account-deletion-scheduler/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Included — the spec's acceptance scenarios (idempotency, partial-failure
isolation, retry, audit log) are concrete testable behaviors, not just HTTP contracts.

**Organization**: Tasks are grouped by user story (US1/US2/US3 from spec.md).

## Format: `[ID] [P?] [Story] Description`

## Path Conventions

Single project (Django backend). All paths relative to `backend/`:
- `apps/accounts/jobs.py`
- `apps/accounts/management/commands/delete_expired_accounts.py`
- `tests/unit/test_delete_expired_accounts.py` (new)

---

## Phase 1: Setup

**Purpose**: Nothing new to scaffold — reuses the existing `accounts` app,
`jobs.py`, and management command. No new dependency, no new file layout.

- [X] T001 Confirm `LOGGING`/root logger config in `backend/config/settings/` sends
      `logging.getLogger(__name__)` output from `apps.accounts` to stdout/stderr
      (Django default), since Heroku captures dyno stdout/stderr as the audit trail
      (research.md § registro auditável) — no code change expected, just verify.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: None. The three user stories touch the same two files but are
sequential edits to independent behaviors (scheduling trigger, failure
isolation, logging) — no shared scaffolding needs to exist first beyond
what's already in the repo.

**Checkpoint**: Skip directly to Phase 3.

---

## Phase 3: User Story 1 - Exclusão automática após a carência (Priority: P1) 🎯 MVP

**Goal**: `delete_expired_accounts` runs automatically at least once every 24h
in production, without any manual trigger, and stays safe if triggered more
than once in the same window (FR-001, FR-002, FR-003, FR-004).

**Independent Test**: Provision the scheduler per `quickstart.md`, create a
test account past the 7-day grace period, wait for/force a run, confirm
deletion happened with zero manual steps; confirm a second run the same day
does not error or double-process.

### Tests for User Story 1

- [X] T002 [P] [US1] Add `test_running_command_twice_is_idempotent` in
      `backend/tests/unit/test_delete_expired_accounts.py`: create one expired
      account, call `jobs.delete_expired_accounts()` twice in a row (mocking
      `supabase_gateway.delete_user`), assert first call returns `1` and
      deletes the user, second call returns `0` and raises no error.
- [X] T003 [P] [US1] Add `test_accounts_within_grace_period_are_untouched` in
      `backend/tests/unit/test_delete_expired_accounts.py`: create an account
      with `deletion_requested_at` 3 days ago, run the job, assert the user
      still exists and `supabase_gateway.delete_user` was never called.

### Implementation for User Story 1

- [X] T004 [US1] Provision the Heroku Scheduler add-on and daily job
      (`python manage.py delete_expired_accounts`) per the steps in
      `specs/003-account-deletion-scheduler/quickstart.md` (ops action, not a
      code change — no `Procfile` entry needed per plan.md's Structure
      Decision).

**Checkpoint**: US1 is independently complete — accounts past grace period
get deleted automatically, daily, safely re-runnable.

---

## Phase 4: User Story 2 - Isolamento de falhas entre contas (Priority: P2)

**Goal**: A failure deleting one account (e.g. Supabase Auth error) does not
block deletion of the other eligible accounts in the same run, and the
failed account stays eligible for automatic retry on the next run (FR-005,
FR-006).

**Independent Test**: Mock `supabase_gateway.delete_user` to raise for one of
several eligible accounts in a single call to `delete_expired_accounts()`;
assert the others are deleted in that same call, and the failed account is
still present and still eligible.

### Tests for User Story 2

- [X] T005 [P] [US2] Add `test_one_account_failure_does_not_block_others` in
      `backend/tests/unit/test_delete_expired_accounts.py`: create 3 expired
      accounts, mock `supabase_gateway.delete_user` to raise for the second
      one and succeed for the other two, call `delete_expired_accounts()`,
      assert it returns `2`, the two succeeding accounts no longer exist, and
      the failing account still exists.
- [X] T006 [US2] Add `test_failed_account_is_retried_next_run` in
      `backend/tests/unit/test_delete_expired_accounts.py` (depends on T005):
      after the failing run in T005's scenario, call
      `delete_expired_accounts()` again with the mock no longer raising,
      assert it returns `1` and the previously-failed account is now deleted.

### Implementation for User Story 2

- [X] T007 [US2] In `backend/apps/accounts/jobs.py`, wrap the
      `supabase_gateway.delete_user` call (and the rest of the per-user
      atomic block) in a `try/except Exception` inside the `for user_id in
      candidate_ids:` loop: on exception, let the `transaction.atomic()`
      block roll back that user's changes, log the error with the user id
      (`logging.getLogger(__name__).exception(...)`), and `continue` to the
      next candidate instead of letting the exception propagate out of the
      function.

**Checkpoint**: US1 + US2 both work independently — automatic runs continue
past a single account's failure, and failures self-heal on the next run.

---

## Phase 5: User Story 3 - Registro auditável de cada execução (Priority: P3)

**Goal**: Every run produces a queryable audit record: count of successful
deletions, count of failures, and a timestamp (FR-007, FR-008).

**Independent Test**: Run `delete_expired_accounts` via the management
command with a mix of succeeding and failing accounts, inspect the emitted
log line, confirm it distinguishes success count from failure count and
includes a timestamp.

### Tests for User Story 3

- [X] T008 [US3] Add `test_command_logs_deleted_and_failed_counts` in
      `backend/tests/unit/test_delete_expired_accounts.py` using pytest's
      `caplog`: run the `delete_expired_accounts` management command via
      `call_command` with one succeeding and one failing account (reusing
      the T005 mock pattern), assert a log record exists containing the
      deleted count (`1`) and the failed count (`1`).

### Implementation for User Story 3

- [X] T009 [US3] In `backend/apps/accounts/jobs.py`, change
      `delete_expired_accounts` to count failures locally (increment a
      `failed` counter in the `except` branch added in T007) and log
      deleted/failed counts from inside the function via
      `logging.getLogger(__name__)`. Keep the existing `int` return
      (successful-deletion count only) — no signature change, so T005/T006's
      `assert ... returns 2` / `returns 1` stay valid.
- [X] T010 [US3] In
      `backend/apps/accounts/management/commands/delete_expired_accounts.py`,
      replace the current `self.stdout.write(...)` line with a
      `logging.getLogger(__name__).info(...)` call (or add it alongside)
      that includes: number deleted, number failed, and
      `timezone.now()` — this is the audit record Heroku's dyno logs
      capture (research.md § registro auditável).

**Checkpoint**: All three user stories work independently; full feature
complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T011 Run the full `backend/tests/unit/test_delete_expired_accounts.py`
      suite plus the existing `backend/tests/contract/test_account_privacy.py`
      to confirm no regression in `jobs.delete_expired_accounts`'s existing
      behavior (anonymization, subscriber count decrement).
- [X] T012 Walk through `specs/003-account-deletion-scheduler/quickstart.md`
      end-to-end against a real or staging Heroku app and confirm the
      Scheduler job is visible and fires as configured.

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): no dependencies.
- No Foundational phase (nothing shared to build first).
- US1 (Phase 3): can start immediately after Setup — no code dependency on
  US2/US3.
- US2 (Phase 4): independent of US1; touches the same file (`jobs.py`) but a
  different concern (failure handling in the loop body).
- US3 (Phase 5): builds on the `except` branch added in US2 (T007) to know
  where to count failures — so do US2 before US3 if working sequentially.
  If parallelizing, coordinate on `jobs.py`'s loop body to avoid merge
  conflicts.
- Polish (Phase 6): after all desired stories are done.

### Parallel Opportunities

- T002 and T003 (US1 tests) — different test functions, same new file:
  parallelizable in authorship, sequential when actually writing to the
  same file.
- T005 can be written in parallel with T002/T003 (different scenarios); T006
  depends on T005's fixture/mock shape.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 (verify logging destination).
2. T002, T003 (idempotency + grace-period tests) — should pass against the
   *existing* `jobs.py` unmodified, since idempotency/grace-period logic is
   already correct.
3. T004 (provision Heroku Scheduler).
4. **STOP and VALIDATE**: this alone closes the compliance gap named in the
   spec (contas paravam de ser excluídas automaticamente) — deploy/demo.

### Incremental Delivery

1. US1 → deploy (compliance gap closed: automatic daily execution).
2. US2 → deploy (failures no longer block the whole batch; auto-retry).
3. US3 → deploy (audit trail for compliance reporting).

---

## Notes

- No `contracts/` tasks: this feature adds no new API/endpoint.
- No new entities/tables (see data-model.md): all tasks are behavior changes
  to `jobs.py` and its management command, plus an ops action (Heroku
  Scheduler provisioning) that lives outside the repo.
- Commit after each task or logical group; stop at any checkpoint to
  validate a story independently.
