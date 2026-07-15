# UI Contract: Interface Hardening

## Auth Heading Contract

- Each auth/password recovery route exposes one primary heading.
- Heading text equals visible task title:
  - Login: "Entrar"
  - Register: "Criar conta"
  - Password reset request: "Recuperar senha"
  - Password reset callback: "Criar nova senha"
- Card styling remains visually consistent.

## Avatar Upload Contract

- Account page shows no visible English file chooser copy.
- Main action label is Portuguese, for example "Alterar foto".
- Selected/canceled/error states use Portuguese copy.
- Remove photo action remains available when a current avatar exists.
- Upload and remove actions expose disabled or progress state while pending.

## Retry Contract

- Retry copy remains "Tentar novamente".
- Retry is keyboard reachable and visibly focused.
- Retry action uses existing product button vocabulary.
- Activation calls the same failed-query retry behavior as before.
- Applies at minimum to:
  - comments thread
  - deck notes page
  - deck suggestions page

## Avatar Display Contract

- Avatar reserves fixed width and height.
- Avatar image loads without shifting sibling content.
- Missing or failed image keeps initials/fallback visible.
- `alt` stays empty where visible neighboring text names the user.

## Transition Contract

- Core controls do not use broad all-property transitions.
- Transitions are limited to color, background, border, opacity, transform, shadow, or equivalent visual-state properties.
- Reduced-motion preference removes non-essential movement.

## Validation Contract

- No horizontal overflow at 360px on audited routes.
- Automated accessibility scan reports zero violations on audited routes.
- Existing sign-in, registration, password reset, account edit, comments retry, notes retry, and suggestions retry workflows still work.
