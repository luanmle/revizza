# Bug Assessment: Sync failure shows false "collection restored from backup" on auth failure

- **Slug**: invalid-refresh-token
- **Created**: 2026-07-15
- **Source**: pasted text
- **Verdict**: valid
- **Severity**: medium

## Report (verbatim or summarized)

> A sincronização falhou e a coleção foi restaurada do backup. Tente novamente. Detalhe: Não foi
> possível entrar: Invalid Refresh Token: Refresh Token Not Found

## Symptom

The add-on shows a sync-failure dialog claiming the collection was rolled back to its pre-sync
backup, when in fact the failure was a Supabase Auth `refresh_token` rejection ("Invalid Refresh
Token: Refresh Token Not Found") — an auth problem that occurs *before* any collection write, so no
backup was ever created or restored. The message is both misleading (no rollback happened) and
unhelpful (it says "tente novamente," but retrying will fail identically until the user re-logs in).

Expected: an auth failure should surface a distinct message telling the user to log in again — not
be conflated with a collection-sync failure that genuinely restored a backup.

## Reproduction

1. Log in to the add-on, obtain a session (`token` + `refresh_token` stored in config).
2. Let the Supabase refresh token become invalid — expires, is revoked, or (session already
   consumed/rotated — Supabase GoTrue's default rotation behavior) [NEEDS CLARIFICATION: exact
   trigger — refresh token TTL expiry vs. rotation reuse vs. manual revocation on the Supabase side;
   not discoverable from this repo alone].
3. Trigger a sync (`Sincronizar agora`, or `on_anki_open`/`chained_native` trigger).
4. `sync_all()` calls `auth.ensure_access_token(config)` (`gui/__init__.py:595`), which calls
   `auth.refresh_session()` → `_token_request()`, which raises `AuthError("Não foi possível entrar:
   Invalid Refresh Token: Refresh Token Not Found")` (`auth.py:39`).
5. The `except Exception` at `gui/__init__.py:615` catches it and shows the generic
   "sincronização falhou e a coleção foi restaurada do backup" message — even though execution never
   reached `sync.sync_decks()` (`gui/__init__.py:614`), so no backup was created (`main/sync.py:288`)
   or restored.

## Suspected Code Paths

- `addon/ankihub_br/gui/__init__.py:594-620` (`sync_all`) — the `try` block wraps
  `auth.ensure_access_token()` (line 595, auth-only, no collection I/O) and
  `client.get_subscribed_decks()` (line 605, network-only) together with `sync.sync_decks()`
  (line 614, the only call that actually creates/restores a backup), then reports every exception
  in that block with one hardcoded "coleção foi restaurada do backup" message.
- `addon/ankihub_br/auth.py:75-88` (`ensure_access_token`) — raises `auth.AuthError` on a missing or
  rejected refresh token; this is the exception type that reaches `sync_all`'s catch-all.
- `addon/ankihub_br/auth.py:15-42` (`_token_request`) — formats the Supabase `error_description`
  into the `AuthError` message, which is where "Invalid Refresh Token: Refresh Token Not Found"
  (Supabase GoTrue's own wording) enters the app.
- `addon/ankihub_br/main/sync.py:284-305` (`sync_decks`) — the actual scope of the backup
  create/restore guarantee (FR-033/FR-039); confirms the guarantee doesn't extend to the auth/token
  and deck-listing steps that precede it in `sync_all`.

## Root Cause Hypothesis

`sync_all`'s single broad `except Exception` treats every failure in its try block as if it were a
mid-sync collection failure, but the block spans three phases with different blast radii: (1) token
refresh (`ensure_access_token`, no collection I/O), (2) fetching the subscribed-deck list (network
only), and (3) `sync.sync_decks` (the only phase that touches the collection and is backup-guarded).
An `AuthError` from phase 1 gets the same "coleção foi restaurada do backup" wording as a genuine
phase-3 failure, which is factually wrong for phases 1–2 and steers the user toward the wrong fix
("tente novamente" instead of "faça login novamente"). Confidence: high — the code path is
unambiguous and directly reproduces the reported message from an `AuthError`.

## Proposed Remediation

**Preferred**: In `sync_all`, catch `auth.AuthError` (and any network/listing failure prior to
`sync.sync_decks`) separately from the generic backup-guarded failure. On `AuthError`, show a message
that doesn't claim a backup restore happened and instead tells the user to log in again (mirroring
the existing `"Faça login no Revizza antes de sincronizar."` wording already used earlier in the same
function for the no-session case) — optionally also clearing the stale session via `auth.sign_out`
so the next `aboutToShow` menu refresh reflects the logged-out state. Keep the current
"sincronização falhou e a coleção foi restaurada do backup" message scoped to exceptions actually
raised from `sync.sync_decks` (i.e., move the `token`/`get_subscribed_decks` calls out of the
backup-implying except-branch, or narrow that branch to wrap only the `sync.sync_decks` call).

**Alternatives**:
- Have `sync.sync_decks` itself carry a marker (e.g., raise a dedicated `SyncCollectionError` wrapper
  around exceptions raised inside its own try block) so any caller can distinguish "backup was
  touched" from "backup was never touched" without `sync_all` needing to know the call sequence.
  More robust against future callers of `sync_all` but a larger change than needed for this bug.

**Files likely to change**:
- `addon/ankihub_br/gui/__init__.py` (`sync_all`)
- `addon/ankihub_br/auth.py` (only if `sign_out`-on-`AuthError` is adopted)
- `addon/tests/unit/` — wherever `sync_all`'s error-message branching is (or should be) unit-tested;
  no existing test file was found covering `sync_all`'s exception handling in this pass
  [NEEDS CLARIFICATION: confirm there is no existing coverage before adding new tests, to avoid
  duplicating an existing fixture].

**Tests to add or update**:
- `sync_all` raises `AuthError` from `ensure_access_token` → shows a "faça login novamente" message,
  not the backup-restore message.
- `sync_all` raises a generic exception from `sync.sync_decks` → still shows the existing
  backup-restore message (regression guard, so the fix doesn't silently swallow the real case FR-039
  is protecting).

## Risks & Considerations

- `sync_all` is called from three different triggers (`manual`, `on_anki_open`,
  `sync_trigger_chained_native`); only `manual` currently shows warnings for some failure paths
  (`sync.can_sync_now()`, no-session case) — decide whether the new auth-failure message should also
  be trigger-gated (e.g., silent on `on_anki_open` to avoid interrupting profile load) or always
  shown, consistent with how the existing generic exception handler currently behaves (always shown,
  no trigger check).
- No collection-state risk from the fix itself — it only changes exception routing/messaging, not
  the backup create/restore logic in `main/sync.py`, which stays untouched.

## Open Questions

- [NEEDS CLARIFICATION: exact upstream cause of the refresh-token rejection — token TTL expiry,
  Supabase refresh-token rotation reuse-detection, or manual revocation — doesn't change the fix
  inside this repo, but would help decide whether `store_session`/`ensure_access_token` also needs a
  rotation-aware retry, which is out of scope for this assessment.]
- [NEEDS CLARIFICATION: whether the auth-failure message should be trigger-gated (see Risks).]
