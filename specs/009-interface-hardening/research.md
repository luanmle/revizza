# Research: Interface Hardening

## Decision: Keep auth heading fix local to each auth page

**Rationale**: `CardTitle` is a generic card label component. Promoting it globally to a heading would create wrong heading levels in nested cards. Local `h1` keeps semantics correct with smallest blast radius.

**Alternatives considered**:

- Change `CardTitle` to render `h1`: rejected, wrong for cards that are not page titles.
- Add polymorphic `asChild`/`as` API to `CardTitle`: rejected for now, more abstraction than four pages need.

## Decision: Hide native file chooser text and trigger it with localized existing controls

**Rationale**: Browser file input chrome can expose English copy. Existing `Label`, `Button`, and hidden file input cover the requirement without new dependency or custom uploader.

**Alternatives considered**:

- Custom dropzone: rejected, too much UI for single avatar upload.
- New upload component: rejected until another upload surface needs same behavior.

## Decision: Use existing `Button` for retry actions

**Rationale**: Retry actions need same focus/hover/disabled vocabulary as rest of product. Existing `Button` already owns this. Use compact link/ghost style based on surrounding layout.

**Alternatives considered**:

- Raw `<button className="underline">`: rejected, audit finding.
- New `RetryButton` component: rejected unless tasks find more than three identical retry blocks needing shared pending/error handling.

## Decision: Keep `UserAvatar` on native image for now, add intrinsic stability and async decode

**Rationale**: Next 16 docs say remote images need dimensions and `remotePatterns`; docs also deprecate `priority` in favor of `preload`. Current avatar URLs are dynamic user data and there is no confirmed remote image allowlist in this feature. Native image with width/height, `decoding="async"`, stable square class, and fallback is smallest safe fix.

**Alternatives considered**:

- Switch to `next/image`: rejected for this feature because remote config and loader policy are outside audit hardening scope.
- Add image proxy or optimizer: rejected, backend/product scope expansion.

## Decision: Replace broad transitions with scoped transition utilities

**Rationale**: Tailwind docs support `motion-reduce:*` and `focus-visible:*` variants. Existing classes can transition color/background/border/shadow/opacity/transform only, avoiding layout animation while preserving state feedback.

**Alternatives considered**:

- Remove all transitions: rejected, would reduce product polish and state feedback.
- Add animation library: rejected, no need for simple component states.

## Decision: Validate with existing frontend gates plus focused a11y/responsive checks

**Rationale**: Existing project already has lint, unit tests, e2e, build, and prior Axe/Playwright baseline. Feature is UI hardening; validation should prove no regression on audited routes and target surfaces.

**Alternatives considered**:

- Add broad new test suite: rejected, overkill for presentational hardening.
- Manual-only validation: rejected, misses regressions in lint/build/e2e.
