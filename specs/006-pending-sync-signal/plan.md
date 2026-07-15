# Implementation Plan: Sinalização de Sincronização Pendente (indicador + onboarding)

**Branch**: `006-pending-sync-signal` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-pending-sync-signal/spec.md`

## Summary

Expose the pending-sync state (already tracked as the `sync_pending` `Notification` from feature 005)
to two existing surfaces instead of building a new signal: an additive `sync_status` field on
`GET /decks/{id}/` for the web deck-detail page (three states: not-yet-synced onboarding,
out-of-date, up-to-date), and an additive `pending_sync` boolean on `GET /decks/?subscribed=1` for
the add-on's "Decks inscritos" menu. One new field, `Subscription.last_synced_at`, distinguishes
"never synced" from "synced and current" — set as a side effect of every successful
delta/full sync call, alongside the existing `sync_pending` resolution logic. No new endpoints, no
new tables, no new notification type.

## Technical Context

**Language/Version**: Python 3.12 (Django backend), TypeScript/Next.js 16 (frontend), Python 3.12
(Anki add-on, `aqt`/`anki`) — existing ratified stack, no new choice.

**Primary Dependencies**: Django REST Framework serializers (existing `DeckDetailSerializer`,
`DeckSubscribedSerializer`), TanStack Query (frontend, already installed), `requests` (add-on client,
already installed) — no new dependency added.

**Storage**: Postgres via Supabase — one new nullable column (`Subscription.last_synced_at`); reuses
the existing `Notification` table from feature 005, no new model.

**Testing**: pytest (backend, extend `apps/catalog/tests/` and `apps/sync/tests/`), Vitest/Playwright
(frontend, existing conventions), pytest (add-on, extend `addon/tests/unit/test_menu.py` and
`test_client.py`).

**Target Platform**: Web (Heroku-hosted Django backend, Next.js frontend) + Anki desktop add-on — no
new platform.

**Project Type**: Web application + Anki add-on (existing `backend/` + `frontend/` + `addon/` split).

**Performance Goals**: Matches SC-001/SC-002 — signal is read synchronously from already-fetched
payloads (deck detail, subscribed-decks list), no additional request needed on either client.

**Constraints**: Must not duplicate the "is there a pending change?" calculation — single source is
the existing `Notification.sync_pending` (FR-007); must not alter the sync delta/full response shape
(`last_synced_at` write is a side effect, mirrors Principle VIII handling from feature 005).

**Scale/Scope**: One new column, two existing serializers extended, one existing view (`
_SubscriberSyncView.get`) extended, one frontend page (`/decks/[id]`) extended with two new copy
states, one add-on menu (`show_subscribed_decks`/`_refresh_menu`) extended with a badge.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Parity Over Reinvention**: Reuses the existing `Notification.sync_pending` signal from feature
  005 instead of a second "what changed" calculation; reuses the existing `DeckDetailSerializer` /
  `DeckSubscribedSerializer` endpoints instead of new routes. Pass.
- **II. Unidirectional Sync**: Purely read-side bookkeeping (`last_synced_at` write, `sync_status`/
  `pending_sync` reads); no add-on-to-backend content write introduced. Pass.
- **III. LGPD by Design**: No new personal data — `last_synced_at` is an operational timestamp about
  the user's own subscription, not a new PII category; no new consent surface implicated. Pass.
- **IV. Secure by Default**: `sync_status` and `pending_sync` are both scoped to `request.user` via
  the existing authenticated serializers (`is_subscribed`, `subscription` already require
  `request.user`) — no cross-user leakage introduced. Pass.
- **V. YAGNI / MVP Scope**: This is the deliberate merge (per spec Assumptions) of two v1.1-adjacent
  drafts into the smallest shared signal; explicitly rejects a new endpoint, a new notification type,
  and a persisted onboarding-wizard state in favor of one field + two additive response fields. Pass.
- **VI. Current Docs & Minimal Code**: No new dependency; reuses existing DRF serializer / TanStack
  Query / `aqt` menu patterns already verified in the codebase (see research.md). Pass.
- **VII. Design Tooling Pipeline**: The `/decks/[id]` onboarding/out-of-date states reuse the existing
  `Alert`/`Badge`/`Card` shadcn primitives already imported on that page — no new component library.
  Must still pass an `impeccable` audit pass on the two new copy states before shipping (frontend
  surface, Constitution VII gate). Pass, contingent on that audit at implementation time.
- **VIII. Sync Fidelity & State Separation (NON-NEGOTIABLE)**: `Subscription.last_synced_at` lives on
  `Subscription` (a web-side bookkeeping table), not on `Note`/`NoteType`/`Card`; the write in
  `_SubscriberSyncView.get` is additive (one more `.update()`/`.save()` call after the existing
  `Notification` resolution) and does not touch `Note.field_values`, `Note.tags`, or any card/
  scheduling data. The sync delta/full response payload is unchanged (contracts/pending-sync.md
  Non-goals). Pass.

No violations — Complexity Tracking table not needed.

**Post-Phase-1 re-check**: Design (data-model.md) confirms `last_synced_at` is a single nullable
column with no migration risk (no backfill logic needed — `None` correctly means "never synced" for
all existing subscriptions), and both new response fields are purely computed/read-only, no write
path added to either serializer. No new violations surfaced. Constitution Check re-passes.

## Project Structure

### Documentation (this feature)

```text
specs/006-pending-sync-signal/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/catalog/
│   ├── models.py                # + Subscription.last_synced_at
│   ├── migrations/               # new migration for the column
│   └── serializers.py            # DeckDetailSerializer + sync_status,
│                                  # DeckSubscribedSerializer + pending_sync
├── apps/sync/
│   └── views.py                  # _SubscriberSyncView.get sets last_synced_at
│                                  # on every successful sync (delta or full)
└── apps/catalog/tests/           # extend with sync_status / pending_sync cases

frontend/
└── src/
    └── app/decks/[id]/page.tsx   # render not_synced_yet / out_of_date / up_to_date

addon/
└── ankihub_br/
    ├── ankihub_br_client/client.py   # get_subscribed_decks() already returns the
    │                                  # new pending_sync field, no client change needed
    └── gui/__init__.py                # show_subscribed_decks / _refresh_menu:
                                        # badge/marker for decks with pending_sync
```

**Structure Decision**: No new app, no new module. Feature lands entirely as additive fields on three
already-existing endpoints/serializers (`DeckDetailSerializer`, `DeckSubscribedSerializer`,
`_SubscriberSyncView`) plus UI changes in the one page and one menu the spec's Anchors already named.
The add-on's HTTP client (`client.py`) needs no change — `get_subscribed_decks()` already returns the
full JSON body, the new field just rides along.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
