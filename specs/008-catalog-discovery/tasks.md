# Tasks: Descoberta avançada do catálogo

**Input**: Design documents from `/specs/008-catalog-discovery/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/catalog-discovery.md](./contracts/catalog-discovery.md), [quickstart.md](./quickstart.md)

**Tests**: Included because `quickstart.md` defines backend contract and frontend validation scenarios for every story.

**Organization**: Tasks are grouped by user story so each story remains independently testable.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm current API/UI docs and local conventions before edits.

- [X] T001 Read current Next.js routing/search-param docs in `frontend/node_modules/next/dist/docs/` before editing `frontend/src/app/decks/page.tsx`
- [X] T002 Resolve and query current TanStack Query docs with Context7 before changing query keys or infinite query behavior in `frontend/src/app/decks/page.tsx`
- [X] T003 Inspect existing shadcn `tabs`, `select`, `badge`, and `skeleton` usage in `frontend/src/components/ui/` and `frontend/design-system/MASTER.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared data needed by catalog tabs, trust fields, and sort.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Add nullable `creator` reference and `is_official` boolean to `Deck` in `backend/apps/catalog/models.py`
- [X] T005 Create catalog migration for `Deck.creator` and `Deck.is_official` with best-effort creator backfill from oldest root moderator in `backend/apps/catalog/migrations/`
- [X] T006 Set `creator=request.user` when publishing a new deck in `backend/apps/sync/views.py`
- [X] T007 Register `Deck.is_official` as staff-editable and keep `creator` visible/read-only in Django admin in `backend/apps/catalog/admin.py`
- [X] T008 Update `make_deck` fixture defaults for optional `creator` and `is_official` coverage in `backend/tests/conftest.py`

**Checkpoint**: Deck rows can store historical creator and official flag; publish sets creator for new decks.

---

## Phase 3: User Story 1 - Navegar por abas do catálogo (Priority: P1) MVP

**Goal**: User can switch between "Catálogo", "Meus baralhos", and "Inscritos" while preserving tag filter and clear empty states.

**Independent Test**: Authenticated user with moderated and subscribed decks opens `/decks`, switches all tabs, and each tab returns exactly its expected deck set.

### Tests for User Story 1

- [X] T009 [P] [US1] Add backend contract tests for anonymous catalog access, authenticated personal tabs, `moderated=1`, `subscribed=1`, combined `tag`, empty results, and `subscribed+moderated` validation in `backend/tests/contract/test_catalog_tabs.py`
- [X] T010 [P] [US1] Add Playwright e2e for `/decks` tabs, URL state, empty states, and pagination reset on tab change in `frontend/tests/e2e/catalog-tabs.spec.ts`

### Implementation for User Story 1

- [X] T011 [US1] Add `moderated=1` filter and `subscribed+moderated` validation to `DeckListView.get_queryset` in `backend/apps/catalog/views.py`
- [X] T012 [US1] Allow unauthenticated `GET /api/v1/decks/` only for general catalog while requiring authentication for `subscribed=1` and `moderated=1` in `backend/apps/catalog/views.py`
- [X] T013 [US1] Keep subscribed serializer compatibility while allowing moderated/catalog modes to use normal deck serializer in `backend/apps/catalog/views.py`
- [X] T014 [US1] Extend deck list query state with `tab`, `tag`, and reset cursor behavior in `frontend/src/app/decks/page.tsx`
- [X] T015 [US1] Render shadcn tabs for "Catálogo", "Meus baralhos", and "Inscritos" in `frontend/src/app/decks/page.tsx`
- [X] T016 [US1] Add tab-specific empty/login states without horizontal overflow at 360px in `frontend/src/app/decks/page.tsx`

**Checkpoint**: User Story 1 works independently without creator/trust display polish.

---

## Phase 4: User Story 2 - Avaliar confiança e atividade do deck (Priority: P2)

**Goal**: Catalog card and deck detail show creator avatar/name, moderator avatars, content update time, and official badge.

**Independent Test**: Deck with creator, active moderators, recent note update, and official flag displays all trust fields in list and detail; moderator cannot self-mark official.

### Tests for User Story 2

- [X] T017 [P] [US2] Add backend contract tests for `creator`, `last_updated_at`, `is_official`, active moderator summaries, creator persistence after moderator removal, and PATCH ignoring/rejecting `is_official` in `backend/tests/contract/test_catalog_trust_fields.py`
- [X] T018 [P] [US2] Add Playwright e2e for creator avatar/name, active moderator avatars, official badge, and updated-at text in `frontend/tests/e2e/catalog-trust.spec.ts`

### Implementation for User Story 2

- [X] T019 [US2] Annotate deck querysets with `last_updated_at` fallback from latest note `mod` to deck `created_at` in `backend/apps/catalog/views.py`
- [X] T020 [US2] Add creator summary, `is_official`, and `last_updated_at` to list/detail serializers in `backend/apps/catalog/serializers.py`
- [X] T021 [US2] Add active moderator summaries to deck detail serializer without exposing moderator emails in `backend/apps/catalog/serializers.py`
- [X] T022 [US2] Ensure `DeckUpdateSerializer` rejects or ignores `is_official` from moderator PATCH payloads in `backend/apps/catalog/serializers.py`
- [X] T023 [US2] Extend frontend deck list/detail types for trust fields in `frontend/src/app/decks/page.tsx` and `frontend/src/app/decks/[id]/page.tsx`
- [X] T024 [US2] Render official badge, creator `UserAvatar`, creator name, and relative updated text on deck cards in `frontend/src/app/decks/page.tsx`
- [X] T025 [US2] Render official badge, creator `UserAvatar`, relative updated text, and active moderator avatar list on detail page in `frontend/src/app/decks/[id]/page.tsx`

**Checkpoint**: User Story 2 works independently when opening one deck directly or viewing catalog cards.

---

## Phase 5: User Story 3 - Ordenar resultados de descoberta (Priority: P3)

**Goal**: User can sort catalog results by recommended, popular, updated, notes, or recent while combining with tab and tag.

**Independent Test**: Applying each sort returns expected stable order; changing tab/tag/sort resets pagination and preserves the other query values.

### Tests for User Story 3

- [X] T026 [P] [US3] Add backend contract tests for all five `sort` values, invalid sort handling, tag+tab+sort combinations, and stable cursor pagination in `backend/tests/contract/test_catalog_sorting.py`
- [X] T027 [P] [US3] Add Playwright e2e for sort select labels, URL state, and cursor reset after sort change in `frontend/tests/e2e/catalog-sorting.spec.ts`

### Implementation for User Story 3

- [X] T028 [US3] Replace fixed catalog ordering with public `sort` mapping and deterministic tie-breakers in `backend/apps/catalog/views.py`
- [X] T029 [US3] Ensure `updated` sort uses annotated `last_updated_at` and remains compatible with cursor pagination in `backend/apps/catalog/views.py`
- [X] T030 [US3] Add shadcn select for sort values and include `sort` in query key/API URL in `frontend/src/app/decks/page.tsx`
- [X] T031 [US3] Reset infinite-query pagination whenever `tab`, `tag`, or `sort` changes in `frontend/src/app/decks/page.tsx`

**Checkpoint**: All user stories work independently and together.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validation, accessibility, and final quality gates across all stories.

- [X] T032 [P] Run backend catalog contract tests from `backend/` with `pytest tests/contract/test_catalog_tabs.py tests/contract/test_catalog_trust_fields.py tests/contract/test_catalog_sorting.py -q`
- [X] T033 [P] Run frontend unit and e2e checks from `frontend/` with `npm run test` and `npm run test:e2e -- --project=chromium`
- [X] T034 Capture Playwright screenshots at 360px and desktop for `/decks` and `/decks/[id]`, then fix any overflow or unreadable trust metadata in `frontend/src/app/decks/page.tsx` and `frontend/src/app/decks/[id]/page.tsx`
- [X] T035 Run design audit against `frontend/design-system/MASTER.md` and remove any nested cards, decorative gradients, weak contrast, or text overflow in `frontend/src/app/decks/page.tsx` and `frontend/src/app/decks/[id]/page.tsx`
- [X] T036 Update quickstart results if validation commands or expected behavior changed in `specs/008-catalog-discovery/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup; blocks all user stories.
- **US1 (Phase 3)**: Depends on Foundational; MVP slice.
- **US2 (Phase 4)**: Depends on Foundational; can run after or alongside US1 once backend list/detail base is stable.
- **US3 (Phase 5)**: Depends on Foundational; uses US2 `last_updated_at` annotation for updated sort.
- **Polish (Phase 6)**: Depends on desired stories being complete.

### User Story Dependencies

- **US1**: No dependency on US2/US3.
- **US2**: No dependency on US1; shares catalog serializers.
- **US3**: Depends on US2 task T019 for `last_updated_at` annotation if `updated` sort is included.

### Parallel Opportunities

- T009 and T010 can run in parallel.
- T017 and T018 can run in parallel.
- T026 and T027 can run in parallel.
- T032 and T033 can run in parallel after implementation.

---

## Parallel Example: User Story 1

```bash
Task: "Add backend contract tests for catalog tabs in backend/tests/contract/test_catalog_tabs.py"
Task: "Add Playwright e2e for catalog tabs in frontend/tests/e2e/catalog-tabs.spec.ts"
```

## Parallel Example: User Story 2

```bash
Task: "Add backend contract tests for trust fields in backend/tests/contract/test_catalog_trust_fields.py"
Task: "Add Playwright e2e for trust fields in frontend/tests/e2e/catalog-trust.spec.ts"
```

## Parallel Example: User Story 3

```bash
Task: "Add backend contract tests for sorting in backend/tests/contract/test_catalog_sorting.py"
Task: "Add Playwright e2e for sorting in frontend/tests/e2e/catalog-sorting.spec.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete T001-T008.
2. Complete T009-T015.
3. Validate `/decks` tabs independently.

### Incremental Delivery

1. Ship US1 tabs.
2. Add US2 trust fields and avatars.
3. Add US3 sort select and stable ordering.
4. Run Phase 6 gates.

### Ponytail Cut

No new endpoint, no persisted sort preference, no custom avatar/tabs/select components, no denormalized
`last_updated_at` until catalog scale proves annotation too slow.
