# Tasks: Interface Hardening

**Input**: Design documents from `/specs/009-interface-hardening/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-hardening.md, quickstart.md

**Tests**: No new TDD tasks requested. Use existing validation gates plus focused manual checks from quickstart.md.

**Organization**: Tasks are grouped by user story so each story can be implemented and verified independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks
- **[Story]**: User story from spec.md
- Every task includes exact file path

## Phase 1: Setup

**Purpose**: Confirm current targets before edits.

- [X] T001 Review audit-derived UI contract in specs/009-interface-hardening/contracts/ui-hardening.md
- [X] T002 Review design-system requirements for pt-BR, focus, 360px, and motion in frontend/design-system/MASTER.md

---

## Phase 2: Foundational

**Purpose**: No shared infrastructure needed; protect scope before story work.

- [X] T003 Confirm no backend, schema, dependency, or new profile-field work is needed for this feature in specs/009-interface-hardening/plan.md
- [X] T004 Inspect current target files for existing patterns before editing: frontend/src/components/ui/card.tsx, frontend/src/components/ui/button.tsx, frontend/src/components/user-avatar.tsx

**Checkpoint**: Scope confirmed. User story work can start.

---

## Phase 3: User Story 1 - Navigate authentication screens accessibly (Priority: P1) MVP

**Goal**: Auth and password reset pages expose one correct primary heading while keeping current visual style.

**Independent Test**: Open each auth route and confirm heading navigation exposes exactly one primary heading matching visible page title.

### Implementation for User Story 1

- [X] T005 [P] [US1] Replace login page title wrapper with a local semantic `h1` preserving current classes in frontend/src/app/(auth)/login/page.tsx
- [X] T006 [P] [US1] Replace register page title wrapper with a local semantic `h1` preserving current classes in frontend/src/app/(auth)/register/page.tsx
- [X] T007 [P] [US1] Replace password reset request title wrapper with a local semantic `h1` preserving current classes in frontend/src/app/(auth)/password-reset/page.tsx
- [X] T008 [P] [US1] Replace password reset callback title wrapper with a local semantic `h1` preserving current classes in frontend/src/app/(auth)/password-reset/callback/page.tsx
- [X] T009 [US1] Remove now-unused `CardTitle` imports from auth pages touched in frontend/src/app/(auth)/login/page.tsx, frontend/src/app/(auth)/register/page.tsx, frontend/src/app/(auth)/password-reset/page.tsx, and frontend/src/app/(auth)/password-reset/callback/page.tsx

**Checkpoint**: US1 independently testable.

---

## Phase 4: User Story 2 - Manage avatar upload entirely in Portuguese (Priority: P1)

**Goal**: Account avatar upload shows no visible English browser file chooser copy and keeps upload/remove behavior.

**Independent Test**: Open account page, choose/cancel/upload/remove avatar, and confirm visible copy stays pt-BR.

### Implementation for User Story 2

- [X] T010 [US2] Replace visible avatar file input with hidden input plus localized trigger control in frontend/src/app/account/page.tsx
- [X] T011 [US2] Show selected avatar file name or Portuguese empty/uploading state near the avatar controls in frontend/src/app/account/page.tsx
- [X] T012 [US2] Preserve existing upload, remove, disabled, and error behavior while clearing canceled/invalid selection states in frontend/src/app/account/page.tsx

**Checkpoint**: US2 independently testable.

---

## Phase 5: User Story 3 - Retry failed actions consistently (Priority: P2)

**Goal**: Retry actions use existing product button vocabulary and visible focus states.

**Independent Test**: Force recoverable errors in comments, notes, and suggestions; tab to retry; activate; confirm same retry behavior.

### Implementation for User Story 3

- [X] T013 [P] [US3] Replace raw retry button with existing Button variant and preserve disabled/loading state during refetch in frontend/src/components/CommentThread.tsx
- [X] T014 [P] [US3] Replace raw retry button with existing Button variant and preserve disabled/loading state during refetch in frontend/src/app/decks/[id]/notes/page.tsx
- [X] T015 [P] [US3] Replace raw retry button with existing Button variant and preserve disabled/loading state during refetch in frontend/src/app/decks/[id]/suggestions/page.tsx

**Checkpoint**: US3 independently testable.

---

## Phase 6: User Story 4 - Preserve performance and visual stability in repeated UI elements (Priority: P2)

**Goal**: Avatars reserve stable space and core controls avoid broad layout-affecting transitions.

**Independent Test**: Load pages with avatars and interact with buttons, badges, and tabs; confirm no layout shift and no layout-property animation.

### Implementation for User Story 4

- [X] T016 [US4] Add intrinsic width, height, async decoding, lazy loading where appropriate, and broken-image fallback handling to frontend/src/components/user-avatar.tsx
- [X] T017 [P] [US4] Replace broad `transition-all` with scoped visual-state transitions, reduced-motion guard, and <=300ms duration in frontend/src/components/ui/button.tsx
- [X] T018 [P] [US4] Replace broad `transition-all` with scoped visual-state transitions, reduced-motion guard, and <=300ms duration in frontend/src/components/ui/badge.tsx
- [X] T019 [P] [US4] Replace broad `transition-all` with scoped visual-state transitions, reduced-motion guard, and <=300ms duration in frontend/src/components/ui/tabs.tsx

**Checkpoint**: US4 independently testable.

---

## Phase 7: Polish & Cross-Cutting Validation

**Purpose**: Prove no regression across audited UI.

- [X] T020 Run formatter if edited frontend source files need it using scripts in frontend/package.json
- [X] T021 Run lint gate and fix any finding using `npm run lint` from frontend/package.json
- [X] T022 Run unit test gate and fix any regression using `npm run test` from frontend/package.json
- [X] T023 Run existing Playwright e2e gate and fix any regression using `npm run test:e2e` from frontend/package.json
- [X] T024 Run production build gate and fix any regression using `npm run build` from frontend/package.json
- [X] T025 Validate quickstart manual checks for headings, pt-BR upload, retry focus, avatar stability, transition duration <=300ms, reduced motion, light/dark, and 360px overflow in specs/009-interface-hardening/quickstart.md
- [X] T026 Run automated accessibility checks on audited routes and fix any violation using Playwright/Axe from frontend/
- [X] T027 Run final Impeccable audit on frontend/src and fix any P0/P1 regression before handoff in frontend/

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Starts immediately.
- **Foundational (Phase 2)**: Depends on Setup.
- **US1 and US2 (P1)**: Depend on Foundational; can run in parallel because files differ.
- **US3 and US4 (P2)**: Depend on Foundational; can run in parallel with each other and after P1 if avoiding shared-file conflicts.
- **Polish (Phase 7)**: Depends on implemented stories.

### User Story Dependencies

- **US1**: No dependency on other stories.
- **US2**: No dependency on other stories.
- **US3**: No dependency on other stories.
- **US4**: No dependency on other stories.

### File Conflict Notes

- T010-T012 all touch `frontend/src/app/account/page.tsx`; do sequentially.
- T016 touches `frontend/src/components/user-avatar.tsx`; independent from retry and auth tasks.
- T017-T019 touch separate shared UI files; can run in parallel.

---

## Parallel Opportunities

- T005-T008 can run in parallel.
- T013-T015 can run in parallel.
- T017-T019 can run in parallel.
- T026-T027 run after implementation and standard validation gates.
- US1, US2, US3, and US4 can be assigned independently after T004, with normal caution for shared imports and validation.

## Parallel Example: User Story 1

```text
Task: "Replace login page title wrapper with a local semantic h1 preserving current classes in frontend/src/app/(auth)/login/page.tsx"
Task: "Replace register page title wrapper with a local semantic h1 preserving current classes in frontend/src/app/(auth)/register/page.tsx"
Task: "Replace password reset request title wrapper with a local semantic h1 preserving current classes in frontend/src/app/(auth)/password-reset/page.tsx"
Task: "Replace password reset callback title wrapper with a local semantic h1 preserving current classes in frontend/src/app/(auth)/password-reset/callback/page.tsx"
```

## Parallel Example: User Story 3

```text
Task: "Replace raw retry button with existing Button variant in frontend/src/components/CommentThread.tsx"
Task: "Replace raw retry button with existing Button variant in frontend/src/app/decks/[id]/notes/page.tsx"
Task: "Replace raw retry button with existing Button variant in frontend/src/app/decks/[id]/suggestions/page.tsx"
```

## Parallel Example: User Story 4

```text
Task: "Replace broad transition-all with scoped visual-state transitions and reduced-motion guard in frontend/src/components/ui/button.tsx"
Task: "Replace broad transition-all with scoped visual-state transitions and reduced-motion guard in frontend/src/components/ui/badge.tsx"
Task: "Replace broad transition-all with scoped visual-state transitions and reduced-motion guard in frontend/src/components/ui/tabs.tsx"
```

---

## Implementation Strategy

### MVP First

1. Complete T001-T004.
2. Complete US1 T005-T009.
3. Validate auth headings independently.

### Incremental Delivery

1. Add US1: semantic auth headings.
2. Add US2: localized avatar upload.
3. Add US3: consistent retry controls.
4. Add US4: avatar stability and scoped transitions.
5. Run T020-T027 before handoff.

### Minimal-Code Rules

- Do not change `CardTitle` globally for US1.
- Do not add upload/dropzone dependency for US2.
- Do not create `RetryButton` unless implementation proves repeated logic needs it.
- Do not switch to `next/image` for US4 unless remote image configuration already safely supports avatar URLs.
- Do not touch backend, database, auth policy, profile bio, or social links in this feature.
