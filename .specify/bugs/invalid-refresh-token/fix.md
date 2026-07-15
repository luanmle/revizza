# Bug Fix: Sync failure shows false "collection restored from backup" on auth failure

- **Slug**: invalid-refresh-token
- **Fixed**: 2026-07-15
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

`sync_all()` now distinguishes `auth.AuthError` (raised by `ensure_access_token` before any
collection write, so no backup exists to restore) from a genuine mid-sync failure inside
`sync.sync_decks` (backup-guarded, FR-033/FR-039). An auth failure now shows "Sessão do Revizza
expirada. Faça login novamente." and signs the stale session out instead of the misleading
"coleção foi restaurada do backup. Tente novamente." message.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `addon/ankihub_br/gui/__init__.py` | modified | Added pure `sync_failure_message(exc)` helper (mirrors the existing `menu_item_states`/`deck_group_title`/`connection_status_message` pure-logic pattern so it's testable without mocking `aqt`); `sync_all`'s except block now calls it and signs out on `auth.AuthError`. |
| `addon/tests/unit/test_menu.py` | added test | `test_sync_failure_message_distinguishes_auth_error_from_collection_failure` pins both message branches. |

## Diff Highlights

```python
def sync_failure_message(exc: Exception) -> str:
    """Mensagem de erro de `sync_all` (bug: invalid-refresh-token).

    `auth.AuthError` é levantado por `ensure_access_token` antes de qualquer
    escrita na coleção — nenhum backup foi criado/restaurado, então a sessão
    expirada/revogada exige novo login, não uma nova tentativa de sync.
    """
    if isinstance(exc, auth.AuthError):
        return f"Sessão do Revizza expirada. Faça login novamente. Detalhe: {exc}"
    return (
        "A sincronização falhou e a coleção foi restaurada do backup. "
        f"Tente novamente. Detalhe: {exc}"
    )
```

```python
    except Exception as exc:
        report_exception(exc)
        if isinstance(exc, auth.AuthError):
            auth.sign_out(config)
            _write_config(config)
        showWarning(sync_failure_message(exc))
        return
```

## Tests Added or Updated

- `addon/tests/unit/test_menu.py::test_sync_failure_message_distinguishes_auth_error_from_collection_failure`
  — asserts an `auth.AuthError` message never claims a backup restore and tells the user to log in
  again; asserts a generic exception still gets the existing backup-restore wording (regression guard
  for FR-039's messaging).

## Local Verification

- Commands run: `.venv/bin/python -m pytest tests/unit -q` (from `addon/`) → **43 passed** (was 42
  before this change; +1 new test).
- Manual checks: none (no live Anki/Supabase session available in this sandbox to reproduce the
  original 401/expired-refresh-token flow end-to-end); relied on the pure-function extraction to make
  the branching logic testable without a real Qt/Anki environment, consistent with this module's
  existing convention (see its docstring: "testes headless importam o pacote sem um Anki gráfico
  rodando").

## Deviations from Assessment

- The assessment's preferred remediation suggested either "moving the token/get_subscribed_decks
  calls out of the backup-implying except-branch" or "narrowing that branch to wrap only
  `sync.sync_decks`." Neither was needed: `auth.AuthError` is a distinct exception type raised only by
  `ensure_access_token`, so branching on `isinstance(exc, auth.AuthError)` inside a single `except
  Exception` cleanly separates the two cases without restructuring the `try` block or changing what's
  covered by the backup-restore guarantee. This is a smaller, more localized diff than either
  alternative in the assessment.
- Extracted the message-selection logic into a standalone `sync_failure_message()` function (not
  explicitly proposed in the assessment) specifically so it has direct unit-test coverage — the
  assessment's "Tests to add or update" section flagged that `sync_all` itself has no existing test
  coverage and is hard to test directly (it imports `aqt` internally). This follows the file's
  established pattern for testable pure logic and satisfies the assessment's test-coverage intent
  without adding `aqt` mocking infrastructure the codebase doesn't otherwise use.
- Did not implement the assessment's "Alternative" (a dedicated `SyncCollectionError` wrapper raised
  from `sync.sync_decks`) — the simpler `isinstance` check fully resolves the reported bug without it;
  left as a documented alternative, not adopted.

## Follow-ups

- The assessment flagged an open question on whether the new auth-failure message should be
  trigger-gated (e.g., silent on `on_anki_open`/`chained_native` to avoid interrupting profile load).
  This fix keeps it always-shown, matching the pre-existing generic exception handler's behavior — no
  new trigger-gating was introduced. Revisit if silent background syncs turn out to interrupt users
  unexpectedly with login prompts.
- No backend/frontend changes were needed — this bug was entirely within the add-on's error-handling
  in `gui/__init__.py`.
