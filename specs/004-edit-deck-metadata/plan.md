# Implementation Plan: Edição de título/descrição/tags do deck pelo moderador

**Branch**: `004-edit-deck-metadata` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-edit-deck-metadata/spec.md`

## Summary

Add a `PATCH /api/v1/decks/{id}/` endpoint, restricted to active moderators of that deck, letting them
update `name`, `description`, and `subject_tags` after publication (currently write-once at import time).
Reuse the existing nh3-based sanitizer for `description` and the existing active-moderator check pattern
already used by the moderator invite/remove endpoints. Add an edit form to the deck detail page, visible
only to active moderators (same visibility rule as the existing moderators screen).

## Technical Context

**Language/Version**: Python 3.12 (backend, Django), TypeScript/Next.js 16 (frontend) — both already ratified stack, no new choice needed.

**Primary Dependencies**: Django REST Framework (existing `generics`/`APIView` patterns in `apps/catalog`), `nh3` (already a dependency, used for note-content HTML sanitization) — no new dependency added.

**Storage**: Postgres via Supabase (existing `Deck` model, no schema change — `name`/`description`/`subject_tags` already exist on `backend/apps/catalog/models.py`).

**Testing**: pytest (backend, existing `apps/catalog` test conventions), Vitest/Playwright (frontend, existing conventions in `frontend/AGENTS.md`).

**Target Platform**: Web (Heroku-hosted Django backend, Next.js frontend) — no new platform.

**Project Type**: Web application (existing `backend/` + `frontend/` split).

**Performance Goals**: Matches SC-001 — edit visible in catalog within 5s of save (a synchronous request/response cycle; no async job needed).

**Constraints**: Only active `DeckModerator` may write (FR-002); title must stay non-empty (FR-003); description sanitized server-side (FR-005); no Anki-side rename side effect (FR-006).

**Scale/Scope**: Single new endpoint + one new frontend edit form on an existing page; no new entities.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Parity Over Reinvention**: No AnkiHub-specific convention is being reinvented here — this is a
  plain authenticated `PATCH` on an existing resource, following the same trailing-slash/cursor
  conventions already used by `apps/catalog`. Pass.
- **II. Unidirectional Sync**: This is a **web-only metadata edit** — no content flows from the add-on,
  and per FR-006 the edited `name` is explicitly NOT pushed into the next sync payload as a deck rename
  in the user's local Anki collection. Pass (see research.md for the explicit sync-payload boundary).
- **III. LGPD**: No personal data touched (deck metadata only). N/A.
- **IV. Secure by Default**: `description` accepts rich text and MUST be sanitized server-side before
  persisting — reusing the existing `apps.notes.sanitize.sanitize_html` allowlist (same one used for
  note fields) rather than inventing a second sanitization policy. HTTPS and rate limiting are already
  enforced globally. Pass.
- **V. YAGNI**: No edit history/audit trail, no optimistic locking, no new dependency — matches
  Assumptions in spec.md. Pass.
- **VI. Minimal Code**: Reuses the existing active-moderator permission check pattern
  (`DeckModeratorListCreateView.post`/`DeckModeratorRemoveView.delete`) instead of introducing a new
  DRF permission class for a single endpoint. Pass.
- **VIII. Sync Fidelity & State Separation**: `name`/`description`/`subject_tags` are Deck-level catalog
  metadata, not Note Content or Card State — this feature does not touch the note/note-type/card sync
  payload at all (FR-006 makes this explicit), so no note-type/deck sync endpoint or business rule is
  being modified. Still, research.md documents where `name` is read during full sync
  (`_deck_payload`) to confirm no unintended propagation, and no automated-test task is needed under
  Principle VIII's payload-vs-scheduling-state clause because no sync endpoint changes. Pass.

No violations — Complexity Tracking table not needed.

**Post-Phase-1 re-check**: Research (Decision 4) surfaced that `_deck_payload` currently sources
`deck_name` from `Deck.name`, which would have broken Principle II/FR-006 (an edited `name` would
silently move the user's local Anki deck on next sync) had it shipped unchanged. Resolved by adding an
immutable `Deck.anki_deck_name` snapshot (data-model.md) that sync reads instead — `name` is now safe
to make freely editable. All other gates unchanged from the pre-design check above. Constitution Check
re-passes.

## Project Structure

### Documentation (this feature)

```text
specs/004-edit-deck-metadata/
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
│   ├── models.py          # add Deck.anki_deck_name (see data-model.md)
│   ├── migrations/        # new migration for anki_deck_name
│   ├── serializers.py     # add DeckUpdateSerializer
│   ├── views.py           # add DeckDetailView.patch (or new DeckUpdateView)
│   ├── urls.py            # PATCH already routes to <uuid:pk>/ (DeckDetailView)
│   └── tests/             # test_deck_update.py (new)
├── apps/sync/
│   └── views.py           # _deck_payload switches deck.name → deck.anki_deck_name
└── apps/notes/
    └── sanitize.py         # reused as-is (sanitize_html) for description

frontend/
└── src/app/decks/[id]/
    ├── page.tsx            # add moderator-only "editar" entry point
    └── edit/page.tsx       # new edit form (name/description/subject_tags)
```

**Structure Decision**: Extends the existing `backend/apps/catalog` (Deck CRUD) and
`backend/apps/sync` (payload builder) apps — no new Django app needed for one endpoint plus
one field. Frontend adds one new route under the existing `decks/[id]/` tree, matching the
`moderators/` sibling page's moderator-only visibility pattern.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
