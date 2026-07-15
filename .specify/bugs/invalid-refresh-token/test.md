# Bug Verification: Sync failure shows false "collection restored from backup" on auth failure

- **Slug**: invalid-refresh-token
- **Tested**: 2026-07-15
- **Assessment**: ./assessment.md
- **Fix**: ./fix.md
- **Result**: verified

## Summary

The verbatim reported error ("Não foi possível entrar: Invalid Refresh Token: Refresh Token Not
Found") no longer produces the misleading "coleção foi restaurada do backup" message; it now
produces "Sessão do Revizza expirada. Faça login novamente." Full add-on unit suite (43 tests,
including auth and backup/restore) passes with no regressions.

## Checks Performed

| Check | Command / Action | Result | Notes |
|-------|------------------|--------|-------|
| Reproduction (post-fix) | `python -c "sync_failure_message(auth.AuthError('Não foi possível entrar: Invalid Refresh Token: Refresh Token Not Found'))"` | pass | Message no longer contains "restaurada do backup"; contains "Faça login novamente" |
| Reproduction — non-auth case still correct | same script, `sync_failure_message(RuntimeError('conexão perdida'))` | pass | Genuine collection-sync failures still get the original backup-restore wording — confirms FR-039's messaging guarantee wasn't weakened |
| Control-flow check | `grep` on `sync_all`'s except block in `gui/__init__.py` | pass | Confirmed the except block at line 630 calls `sync_failure_message(exc)` and signs out only on `auth.AuthError` (lines 632-634), matching fix.md's diff |
| New/updated test | `.venv/bin/python -m pytest tests/unit/test_menu.py -q -v` (from `addon/`) | pass | 5/5, including `test_sync_failure_message_distinguishes_auth_error_from_collection_failure` |
| Regression suite | `.venv/bin/python -m pytest tests/unit -q` (from `addon/`) | pass | 43/43 (was 42 pre-fix +1 new test) |
| Targeted regression — auth + backup/restore | `.venv/bin/python -m pytest tests/unit/test_auth.py tests/unit/test_sync_failure_recovery.py -q` | pass | 10/10 — `auth.AuthError` semantics and the FR-033/FR-039 backup/restore roundtrip both unaffected by the fix |
| Lint / type-check | — | not-run | No lint/type-check tooling configured for the add-on (`pytest.ini` only; no ruff/flake8/mypy config found in `addon/`) |

## Output Excerpts

```
'Sessão do Revizza expirada. Faça login novamente. Detalhe: Não foi possível entrar: Invalid Refresh Token: Refresh Token Not Found'
PASS: verbatim reported error no longer produces the misleading backup-restore claim
```

```
...........................................                              [100%]
43 passed in 1.73s
```

## Residual Risks

- Could not exercise the true end-to-end path (`sync_all()` itself, invoked from a real Anki menu
  action against a live Supabase instance with an actually-expired/revoked refresh token) — no live
  Anki desktop profile or Supabase project is available in this sandbox. Verification instead
  exercised the extracted pure `sync_failure_message()` function directly with the exact reported
  error string, plus a source-level check that `sync_all`'s except block wires that function in
  correctly. This mirrors the fix's own stated approach (fix.md's Local Verification) and this
  module's established testing convention of extracting pure logic rather than mocking `aqt`.
- `report_exception(exc)` (Sentry/error-reporting side effect) still fires for `AuthError` exactly as
  before — unchanged, not in scope of this bug.
- The open question from assessment.md about whether the new message should be trigger-gated (silent
  on `on_anki_open`/`chained_native`) remains unresolved, as noted in fix.md's Follow-ups — not a
  regression, just deferred scope.

## Recommendation

Close the bug — the message-selection logic is verified against the exact reported error string, the
generic-failure branch is confirmed unchanged (no weakening of the FR-039 backup-restore guarantee's
messaging), and the full add-on regression suite passes. The only gap is a live end-to-end run through
a real Anki+Supabase session, which isn't reproducible in this environment; if that matters, do one
manual check in a real profile before the next release, but it doesn't block closing this ticket.
