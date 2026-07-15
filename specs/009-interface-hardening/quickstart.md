# Quickstart: Interface Hardening Validation

## Prerequisites

- Backend and frontend env already configured as in existing project setup.
- Run commands from `frontend/`.

## Static Gates

```bash
npm run lint
npm run test
npm run build
```

Expected:

- Lint passes with no avatar image warning.
- Unit tests pass.
- Production build passes.

## Existing E2E Gate

```bash
npm run test:e2e
```

Expected:

- Existing Playwright suite passes.

## Manual/A11y Checks

Start app:

```bash
npm run dev
```

Check these routes at 360px and desktop, light and dark theme:

- `/`
- `/login`
- `/register`
- `/password-reset`
- `/password-reset/callback`
- `/decks`
- `/account`
- `/decks/[id]/notes`
- `/decks/[id]/suggestions`

Expected:

- No horizontal overflow at 360px.
- Auth pages expose one primary heading matching visible title.
- Avatar upload area shows only Portuguese visible copy.
- Retry actions are reachable by keyboard and show focus ring.
- Avatar image loading does not shift nearby text.
- Buttons, badges, and tabs keep state feedback without layout animation.
- Reduced-motion preference keeps UI usable.

## Contract References

- UI behavior contract: [contracts/ui-hardening.md](./contracts/ui-hardening.md)
- UI state model: [data-model.md](./data-model.md)
