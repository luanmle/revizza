# Implementation Plan: Interface Hardening

**Branch**: `009-interface-hardening` | **Date**: 2026-07-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-interface-hardening/spec.md`

## Summary

Fix audited UI hardening gaps with smallest safe frontend diff: local semantic headings on auth pages, localized avatar upload control, consistent retry buttons, stable avatar rendering, and scoped transitions. No new product feature, no new dependency, no backend change.

## Technical Context

**Language/Version**: TypeScript 5, React 19.2.4, Next.js 16.2.10

**Primary Dependencies**: Existing `@base-ui/react`, shadcn-style local components, Tailwind CSS 4.3.2, TanStack Query 5.101.2, Playwright, Vitest

**Storage**: N/A; feature changes presentation and interaction only

**Testing**: `npm run lint`, `npm run test`, `npm run test:e2e`, `npm run build`; focused manual a11y/responsive checks

**Target Platform**: Web app, desktop and mobile browser, 360px minimum viewport

**Project Type**: Frontend web application inside existing monorepo

**Performance Goals**: No visible layout shift from avatars; transitions complete within 300ms; no added runtime dependency

**Constraints**: 100% pt-BR visible copy, WCAG AA focus/semantics, no horizontal overflow at 360px, light/dark parity, reduced-motion support

**Scale/Scope**: Five small UI surfaces: auth screens, account avatar upload, retry controls in comments/notes/suggestions, shared avatar component, shared button/badge/tabs transition classes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Parity Over Reinvention**: Pass. No backend/API/sync convention touched.
- **II. Unidirectional Sync**: Pass. No deck/note content sync touched.
- **III. Privacy & LGPD**: Pass. Existing profile/avatar personal data behavior preserved; no new data field.
- **IV. Secure by Default**: Pass. No auth/storage/security boundary expanded.
- **V. MVP Scope Discipline**: Pass. Bio/social links excluded. Only audit hardening.
- **VI. Current Docs & Minimal Code**: Pass. Checked Next 16 image docs and Tailwind motion/focus docs. Plan chooses existing components/native browser features over new dependency.
- **VII. Design Tooling Pipeline**: Pass. Uses existing `frontend/design-system/MASTER.md`, Product mode, pt-BR, 360px, focus, reduced motion.
- **VIII. Sync Fidelity & State Separation**: Pass. No note/deck data model, sync endpoint, or scheduling-adjacent behavior touched.

## Project Structure

### Documentation (this feature)

```text
specs/009-interface-hardening/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ui-hardening.md
└── tasks.md
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   ├── register/page.tsx
│   │   │   ├── password-reset/page.tsx
│   │   │   └── password-reset/callback/page.tsx
│   │   ├── account/page.tsx
│   │   └── decks/[id]/
│   │       ├── notes/page.tsx
│   │       └── suggestions/page.tsx
│   └── components/
│       ├── CommentThread.tsx
│       ├── user-avatar.tsx
│       └── ui/
│           ├── badge.tsx
│           ├── button.tsx
│           └── tabs.tsx
└── tests/
```

**Structure Decision**: Use existing frontend files only. Add no new source directory unless tasks discover repeated retry markup needs a tiny local helper; default is direct replacement in affected files.

## Complexity Tracking

No constitution violations. No extra complexity accepted.

## Post-Design Constitution Check

Pass. `research.md`, `data-model.md`, `contracts/ui-hardening.md`, and `quickstart.md` keep scope frontend-only, add no dependency, preserve pt-BR/a11y/design-system gates, and do not touch backend, sync, notes, decks, or scheduling state.
