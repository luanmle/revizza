# Implementation Plan: Add-on Note Actions & Sync Stability

**Branch**: `010-addon-note-actions` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-addon-note-actions/spec.md`

## Summary

Add three note-scoped actions to the Anki add-on — "Ver no Revizza" and "Ver histórico" on the reviewer bottom bar, and a "Sugerir mudança" button in the note editor — plus a hardened, automated sync-stability test suite. Navigation works by linking to a new backend GUID-addressed redirect endpoint (`/go/note/<guid>/` and `/…/history/`) that resolves the note's stable GUID to its public web page; the suggest flow resolves the GUID to the platform note id and reuses the existing change-suggestion pipeline (no new upstream content write — it is a proposal, per Principle II). A local pre-check compares the edited note against a per-note snapshot cached at last sync to show "nada a sugerir" offline before opening the form.

## Technical Context

**Language/Version**: Python 3.12 (backend + add-on venvs), TypeScript / Next.js 16 + React 19 (frontend)

**Primary Dependencies**: Backend — Django + DRF; Add-on — `aqt`/`anki` native libs, `requests`, `peewee` (local cache); Frontend — Tailwind 4 + shadcn/ui

**Storage**: Postgres via Supabase (backend, unchanged schema for notes/suggestions); add-on local SQLite cache in `user_files/` (`SyncStateCache`, one new column)

**Testing**: pytest (backend + add-on), Vitest/Playwright (frontend)

**Target Platform**: Anki desktop (Qt6) add-on; Heroku-hosted DRF API; web app

**Project Type**: Web application + desktop add-on (three subtrees: `backend/`, `frontend/`, `addon/`)

**Performance Goals**: Navigation opens the note in the browser in <5s (SC-001); suggestion round-trip is a single POST after one resolve GET

**Constraints**: Add-on network runs off the Qt thread (`QueryOp`), never blocking the UI (FR-009); the diff pre-check works offline (FR-008); sync must never touch local Card State (Principle VIII, FR-013)

**Scale/Scope**: Per-note actions on subscribed decks; no bulk-from-Anki flow (single note per suggestion)

## Constitution Check

*GATE: evaluated against `.specify/memory/constitution.md` v1.3.0.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Parity Over Reinvention | ✅ Pass | Buttons mirror AnkiHub's own add-on (reviewer link + editor suggest button + view-history). Reuses existing suggestion pipeline and cursor-paginated suggestion list. |
| II. Unidirectional Sync (NON-NEGOTIABLE) | ✅ Pass | From-Anki "Sugerir mudança" enters the suggestion → moderation → sync-queue pipeline; it is a **proposal**, never a direct content push or republish. No add-on→backend write bypasses moderation. Explicitly asserted by test tasks. |
| III. Privacy & LGPD | ✅ Pass (reviewed) | Suggestion submission stays tied to the authenticated author (FR-010). Public read (FR-005a) is scoped to **deck content** (note detail) and the note-filtered suggestion list — community content already visible to every subscriber, on decks that are non-private by design (PRD §2.3). No personal-account data is exposed; comment threads and write actions stay gated. |
| IV. Secure by Default | ✅ Pass | From-Anki suggestion HTML flows through the **existing** server-side sanitizer and the existing `@suggestion_ratelimit`. GUID is a non-secret note key; enumeration only reaches already-public pages. All add-on↔backend traffic HTTPS. |
| V. MVP Scope Discipline (YAGNI) | ✅ Pass | No deferred non-goal pulled forward. Single-note suggestion only; bulk stays web-only. No new dependency — reuses `requests`, `peewee`, existing endpoints. |
| VI. Current Docs & Minimal Code | ✅ Pass | Anki reviewer bottom-bar and editor-button hook signatures verified against installed Anki source/stubs before coding (research.md). One new cache column, one shared resolver helper, two thin redirect views — no new abstraction. |
| VII. Design Tooling Pipeline | ✅ Pass | Frontend surface is small: read-only rendering of the existing note page for anonymous viewers + initialising the suggestions filter from the URL. Any visible change passes the impeccable gate and stays functional at 360px (FR-053). |
| VIII. Sync Fidelity & State Separation (NON-NEGOTIABLE) | ✅ Pass | New per-note snapshot (field hash) is **Note Content** only, cached beside the existing `SyncStateCache` — never Card State. No action reads or writes scheduling/`revlog`. US4 + FR-013 add automated tests asserting a sync payload update leaves local card scheduling untouched, covering the full-resync fallback path. |

**Result**: All gates pass. No Complexity Tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/010-addon-note-actions/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── note-resolve.md  # GUID redirect + JSON resolve endpoints
│   └── addon-actions.md # add-on UI actions ↔ backend contract
└── tasks.md             # /speckit-tasks output (not created here)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   └── notes/
│       ├── views.py           # + GuidRedirectView, GuidHistoryRedirectView, NoteResolveView
│       ├── urls.py            # + /go/note/<guid>/, /go/note/<guid>/history/, /notes/resolve/
│       ├── serializers.py     # + NoteResolveSerializer (note_id, deck_id, web_url, history_url)
│       └── permissions/perms  # note detail read → AllowAny (read-only)
│   └── suggestions/
│       └── views.py           # DeckSuggestionListView read → AllowAny (read-only, note-filtered)
└── config/
    └── settings.py            # + FRONTEND_BASE_URL (redirect target)

frontend/
└── src/app/decks/[id]/
    ├── notes/[noteId]/page.tsx    # render read-only for anonymous viewer
    └── suggestions/page.tsx       # init note_id filter from ?note_id= searchParam

addon/ankihub_br/
├── gui/
│   ├── __init__.py            # register reviewer + editor hooks in setup()
│   ├── reviewer.py            # (new) bottom-bar "Ver no Revizza" / "Ver histórico"
│   └── editor.py              # (new) editor "Sugerir mudança" button + dialog
├── db/models.py              # + field_hash column on SyncStateCache; snapshot on sync
├── main/sync.py              # record field snapshot/hash when applying notes
├── ankihub_br_client.py      # + resolve_note(guid) and submit_change_suggestion(...)
└── tests/
    └── test_sync_stability.py # (new) idempotency/interrupt/edge-case + scheduling-immutability
```

**Structure Decision**: Existing three-subtree web-app + add-on layout. Backend changes are additive (new views/URLs, one settings value, two read endpoints relaxed to `AllowAny`). Add-on gains two small GUI modules and one cache column. Frontend reuses existing pages with minimal read-only/query-param handling.

## Complexity Tracking

> No Constitution Check violations — table intentionally empty.
