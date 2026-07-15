# Data Model: Interface Hardening

No persistent data model change.

## UI State: Auth Page Heading

- **Fields**:
  - `visibleTitle`: page title shown to user
  - `semanticLevel`: primary page heading level
- **Rules**:
  - One primary heading per auth/password recovery page.
  - Heading text matches visible task title.

## UI State: Avatar Upload

- **Fields**:
  - `selectedFileName`: selected file name or empty state
  - `uploadState`: idle, selected, uploading, error
  - `errorMessage`: localized failure reason
- **Rules**:
  - Visible copy is Brazilian Portuguese.
  - Native browser file chooser copy is not visible in normal page layout.
  - Invalid, canceled, slow, and failed upload states leave clear next action.

## UI State: Retry Action

- **Fields**:
  - `label`: retry copy
  - `status`: idle, retrying, disabled
  - `target`: comments, notes, suggestions
- **Rules**:
  - Keyboard focus visible.
  - Activation retries failed operation without full page refresh.
  - Visual treatment matches existing product controls.

## UI State: Avatar Display

- **Fields**:
  - `avatarUrl`: optional user image URL
  - `name`: optional display name
  - `fallbackInitial`: first usable name character or fallback mark
- **Rules**:
  - Stable square space is reserved before image load.
  - Image failure keeps usable fallback behavior.
  - Decorative avatar image remains silent when adjacent author name already provides identity.

## UI State: Component Transition

- **Fields**:
  - `component`: button, badge, tab trigger
  - `transitionedProperties`: visual-state properties only
  - `reducedMotion`: user preference state
- **Rules**:
  - No layout-affecting transition.
  - Reduced-motion preference disables or shortens non-essential motion.
