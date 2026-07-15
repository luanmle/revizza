# Implementation Plan: Descoberta avançada do catálogo

**Branch**: `008-catalog-discovery` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-catalog-discovery/spec.md`

## Summary

Enrich the existing deck catalog instead of adding new surfaces: extend `GET /api/v1/decks/` with
`moderated`, `subscribed`, `tag`, and `sort` combinations; add creator, official badge, and content
freshness fields to list/detail responses; show tabs, sort select, creator avatar, moderator avatars,
and clearer empty states in the existing `/decks` and `/decks/[id]` pages.

## Technical Context

**Language/Version**: Python 3.12 + Django 5.x backend; TypeScript + Next.js 16.2 frontend.

**Primary Dependencies**: Django REST Framework cursor pagination and serializers; existing
TanStack Query, shadcn/ui (`tabs`, `select`, `badge`, `skeleton`), `UserAvatar`, Tailwind 4. No new
dependency planned.

**Storage**: Existing Postgres-backed Django models. Add two Deck fields: `creator` and
`is_official`; derive `last_updated_at` from deck notes instead of storing it.

**Testing**: Backend pytest contract tests under `backend/tests/contract/`; frontend Vitest plus
Playwright screenshots/e2e per `frontend/AGENTS.md`.

**Target Platform**: Web application: Django API + Next.js frontend.

**Project Type**: Existing web app with `backend/` and `frontend/` split.

**Performance Goals**: Catalog tab/sort/filter changes feel immediate for MVP-sized catalog; no
visible page duplication/skips while paginating one unchanged query state.

**Constraints**: Cursor pagination ordering must be deterministic; `subscribed` behavior consumed by
the add-on must remain compatible; official badge is staff/admin-controlled; 360px viewport must not
scroll horizontally; implementation must consult current docs before using library APIs.

**Scale/Scope**: One catalog endpoint, one deck detail endpoint, one model migration, two frontend
routes already present. No new public endpoint.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Parity Over Reinvention**: Keeps existing catalog and cursor pagination conventions. Pass.
- **II. Unidirectional Sync**: Feature changes web catalog discovery metadata only. Sync payloads and
  local Anki card state are not modified. Pass.
- **III. Privacy & LGPD**: Creator/moderator display uses existing profile names and public avatars;
  deleted or missing profiles fall back to unavailable display. No new optional data use. Pass.
- **IV. Secure by Default**: No rich-text write path added. Official flag has no moderator-controlled
  public mutator. Pass.
- **V. MVP Scope Discipline**: No persisted sort preference, no new search system, no moderation role
  hierarchy, no extra endpoint. Pass.
- **VI. Current Docs & Minimal Code**: DRF docs checked for cursor pagination and restricted ordering
  exposure; implementation phase must check Next/TanStack/shadcn docs before API usage. Pass.
- **VII. Design Tooling Pipeline**: `ui-ux-pro-max` foundation read from
  `frontend/design-system/MASTER.md`; `impeccable` product register loaded. Plan requires Playwright
  360px + desktop visual checks before completion. Pass.
- **VIII. Sync Fidelity & State Separation**: Does not touch note content sync payloads or card
  scheduling state. `last_updated_at` is read-only catalog metadata derived from Note content
  timestamps. Pass.

No violations. Complexity Tracking not needed.

**Post-Phase-1 re-check**: Design artifacts preserve all gates. `Deck.creator` is the only extra field
beyond the requested official flag; it is required to satisfy the spec assumption that creator remains
historical after moderator removal, without storing a duplicate personal-data snapshot. Pass.

## Project Structure

### Documentation (this feature)

```text
specs/008-catalog-discovery/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── catalog-discovery.md
└── tasks.md
```

### Source Code (repository root)

```text
backend/
├── apps/catalog/
│   ├── models.py          # Deck.creator, Deck.is_official
│   ├── migrations/        # migration + creator backfill from original moderator when possible
│   ├── serializers.py     # creator/moderators/last_updated_at/is_official fields
│   ├── views.py           # moderated filter, safe sort mapping, annotations
│   └── tests/             # existing app code; project tests live under backend/tests/
└── tests/contract/
    └── test_catalog_discovery.py

frontend/
├── src/app/decks/
│   ├── page.tsx           # tabs, sort select, enriched cards, empty states
│   └── [id]/page.tsx      # creator/moderator avatars, official badge, updated-at
└── src/components/
    └── user-avatar.tsx    # reuse existing fallback/avatar component
```

**Structure Decision**: Extend existing catalog list/detail flow. Adding endpoints or a separate
"my decks" route would duplicate the same list behavior and break the already-used subscribed query
pattern.
