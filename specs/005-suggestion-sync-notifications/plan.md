# Implementation Plan: Notificações de Suggestion/Sync

**Branch**: `005-suggestion-sync-notifications` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-suggestion-sync-notifications/spec.md`

## Summary

Add a new `apps/notifications` Django app with a single `Notification` model, fed by explicit
calls (no signals) from three existing hot paths — suggestion decision (`apps/suggestions/decisions.py`),
suggestion creation (`apps/suggestions/views.py`), and subscriber sync (`apps/sync/views.py`) — plus a
small REST surface (list/unread-count/mark-read) and a `NotificationBell` in the existing site header,
polled via TanStack Query. No email/push/websocket channel; in-app only (FR-009).

## Technical Context

**Language/Version**: Python 3.12 (Django backend), TypeScript/Next.js 16 (frontend) — existing ratified stack, no new choice.

**Primary Dependencies**: Django REST Framework (`generics`/`APIView`, existing `DefaultCursorPagination`), TanStack Query (frontend, already installed) — no new dependency added.

**Storage**: Postgres via Supabase — one new table (`Notification`), FKs into existing `accounts.User`, `catalog.Deck`, `suggestions.Suggestion`, `notes.Note`.

**Testing**: pytest (backend, new `apps/notifications/tests/`), Vitest/Playwright (frontend, existing conventions).

**Target Platform**: Web (Heroku-hosted Django backend, Next.js frontend) — no new platform.

**Project Type**: Web application (existing `backend/` + `frontend/` split).

**Performance Goals**: Matches SC-001/SC-002 — decision-to-notification visible within seconds (synchronous write in the same request, no async job/queue needed at this scale).

**Constraints**: In-app channel only, no email/push (FR-009); at most one active `sync_pending` notification per (recipient, deck) (FR-005); sync-pending resolution must not write to Note/Card/scheduling data (Principle VIII).

**Scale/Scope**: One new Django app, one new model, 4 new endpoints, 3 existing view files touched to add trigger calls, one new frontend component.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Parity Over Reinvention**: Reuses `DefaultCursorPagination` (same `next`/`previous` cursor convention as every other list endpoint), `is_active_deck_moderator`/`DeckModerator.Status.ACTIVE` filter pattern, and `BaseModel` (UUID pk + timestamps). No new pagination or permission scheme invented. Pass.
- **II. Unidirectional Sync**: Notifications are pure web-side bookkeeping; nothing here lets the add-on push data upstream. The `sync_pending` resolve step reads the sync response's success (deck + user) but writes only to `Notification`, never to `Note`/`NoteType`/`Card`. Pass.
- **III. LGPD by Design**: Notification content is transactional (result of the user's own actions/subscriptions), not marketing communication — no separate opt-in consent required. No new PII beyond the existing recipient FK. Pass.
- **IV. Secure by Default**: Notification body never carries raw user HTML — `rejection_reason` is read live from `Suggestion.rejection_reason`, which is already plain text (not sanitized-HTML content) captured at decision time by the existing suggestion flow; no new sanitization surface introduced. Endpoints are authenticated, scoped to `request.user` (no cross-user notification leakage by construction — every query filters `recipient=request.user`). Pass.
- **V. YAGNI / MVP Scope**: This feature was a deferred v1.1 item in PRD §2.3; this spec is the explicit, deliberate decision to pull it into scope now (not creep) because the suggest→moderate→propagate loop is otherwise silent. Scope stays in-app only, no push/email/websocket, no generic event bus, no per-notification-type template system. Pass.
- **VI. Current Docs & Minimal Code**: No new dependency; reuses existing DRF/TanStack Query patterns verified in the codebase (see research.md). Pass.
- **VII. Design Tooling Pipeline**: `NotificationBell` reuses the existing `DropdownMenu`/`DropdownMenuContent`/`DropdownMenuItem` shadcn primitives already imported in `SiteHeader.tsx` — no new component library, consistent with the ui-ux-pro-max → impeccable pipeline conventions already applied elsewhere. Pass.
- **VIII. Sync Fidelity & State Separation (NON-NEGOTIABLE)**: The only change inside `apps/sync/views.py` is one `.update()` against the new `Notification` table (resolving `sync_pending`) after a successful `DeltaView`/`FullView` call — it does not read, filter, or mutate `Note.field_values`, `Note.tags`, `NoteType`, or any card/scheduling data. research.md documents the exact call site and confirms no interaction with the Note Content/Card State boundary. Pass.

No violations — Complexity Tracking table not needed.

**Post-Phase-1 re-check**: Design (data-model.md) confirmed the `sync_pending` uniqueness is enforced by a partial DB constraint rather than app-level locking, and the resolve step in `_SubscriberSyncView` is additive (one `.update()` call, no change to existing sync response shape). No new violations surfaced. Constitution Check re-passes.

## Project Structure

### Documentation (this feature)

```text
specs/005-suggestion-sync-notifications/
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
├── apps/notifications/        # new app
│   ├── models.py               # Notification(BaseModel)
│   ├── services.py             # notify_suggestion_decided, notify_new_suggestion
│   ├── serializers.py          # NotificationSerializer
│   ├── views.py                # list, unread-count, read, read-all
│   ├── urls.py
│   ├── migrations/
│   ├── management/commands/
│   │   └── purge_read_notifications.py   # FR-010, 90-day retention
│   └── tests/
├── apps/suggestions/
│   ├── decisions.py            # call notify_suggestion_decided() inside existing atomic block
│   └── views.py                # call notify_new_suggestion() in the 3 creation entrypoints
├── apps/sync/
│   └── views.py                # _SubscriberSyncView resolves active sync_pending after successful sync
└── config/
    ├── settings/base.py        # register apps.notifications
    └── urls.py                 # include apps.notifications.urls

frontend/
└── src/
    ├── lib/notifications.ts    # types + api.get/api.post wrappers
    └── components/
        └── SiteHeader.tsx      # add NotificationBell (~line 44-49, next to ThemeToggle)
```

**Structure Decision**: New Django app `apps/notifications` (one model, one cross-cutting concern
touching three existing apps at explicit call sites) rather than folding `Notification` into
`apps/suggestions` — it's referenced by `suggestions`, `sync`, and eventually any future trigger,
so it deserves its own app boundary rather than living inside the app that happens to fire it most.
Frontend adds one component to the existing global header; no new route/page needed.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
