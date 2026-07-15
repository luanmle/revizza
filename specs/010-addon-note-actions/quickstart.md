# Quickstart & Validation: Add-on Note Actions & Sync Stability

Runnable validation for the feature. References contracts/ and data-model.md rather than duplicating them.

## Prerequisites

- Backend running with `FRONTEND_BASE_URL` set (see contracts/note-resolve.md → Settings).
- A published Revizza deck with at least one note, and an add-on user **subscribed** to it and **synced** (so `SyncStateCache` holds the note's GUID + `field_hash`).
- Add-on installed in a real Anki profile for the manual matrix; headless pytest for the automated suite.

## Automated checks

```bash
# Backend: resolution + public reads + suggestion reuse
cd backend && pytest apps/notes/tests apps/suggestions/tests -q

# Add-on: UI action logic + sync stability suite
cd addon && pytest tests/test_sync_stability.py tests -q
```

Expected: all green. The sync-stability suite (FR-014) asserts idempotency, interrupt/resume convergence, content edge cases, note-type-change full-resync fallback, and — the Principle VIII gate — that a captured card-state fixture (ease/interval/due/revlog) is byte-identical before and after any sync payload application.

## Manual validation (real Anki profile)

### US1 — "Ver no Revizza"
1. Review a card from the synced deck → click "Ver no Revizza" on the bottom bar.
   - **Expect**: default browser opens on `/decks/{deck}/notes/{note}` showing that exact note (SC-001, <5s). ✅
2. Review a card from a non-Revizza deck.
   - **Expect**: no "Ver no Revizza" button (FR-001). ✅
3. Delete the note on the web, then click the button.
   - **Expect**: "nota não encontrada no Revizza" (US1 #3). ✅

### US2 — "Sugerir mudança" from Anki
1. Open a synced note in the editor, change a field, click "Sugerir mudança".
   - **Expect**: dialog asks category + justification; on submit, a `201` toast; suggestion visible on the web Community Suggestions with the edited content (FR-007, SC-002/SC-003). ✅
2. Open the button without changing anything.
   - **Expect**: "Nada a sugerir" (FR-008), no form, no network. ✅
3. Expire/clear the add-on session, then submit.
   - **Expect**: prompted to log in; drafted fields + justification preserved (FR-009/FR-010). ✅

### US3 — "Ver histórico"
1. For a note with suggestions, click "Ver histórico".
   - **Expect**: browser opens the suggestions view filtered to that note. ✅
2. For a note with no suggestions.
   - **Expect**: same view, empty state (not an error) (US3 #2). ✅

### US4 — Sync stability (manual matrix, pre-release; FR-014a)
Run against a real profile and confirm a consistent collection **and untouched scheduling** after each:

| # | Scenario | Expected |
|---|----------|----------|
| 1 | Sync an unchanged deck 20× | zero local modifications (SC-004) |
| 2 | Kill Anki mid-sync, reopen, sync | converges, no duplicate/orphan notes (FR-012) |
| 3 | Remote note with empty / very large / special-char fields | applies cleanly (FR-013) |
| 4 | Remote subdeck move | note relocated, scheduling intact |
| 5 | Remote note-type structural change | full-resync fallback; **card due dates/intervals/review history unchanged** (Principle VIII, SC-005) |
| 6 | Protected field/tag present, remote edits it | local protected value preserved (Principle II) |

## Done signals

- All automated suites green; every manual scenario above checks out.
- No scheduling loss or protected-field overwrite across the matrix (SC-005 = zero).
