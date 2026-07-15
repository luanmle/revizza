# Implementation Plan: Edição de Perfil (Foto e Dados Adicionais)

**Branch**: `007-profile-edit-avatar` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-profile-edit-avatar/spec.md`

## Summary

Estender `User` com um campo de avatar (caminho de imagem em storage, não binário), tornar
`target_career`/`target_board` editáveis via `ProfileUpdateSerializer`/`MeView.patch` (hoje só
aceita `name`), e expor o avatar (ou um placeholder) nos três pontos de autoria já existentes:
sugestões (`apps.suggestions`), comentários (`apps.discussions`) e lista de moderadores de deck
(`apps.catalog`). Upload é multipart direto para o Django (não presigned-URL), porque a validação
de tipo/tamanho/dimensão real do arquivo (FR-002/FR-003) deve acontecer no servidor antes de
qualquer coisa ser persistida ou publicada — Pillow (`Pillow>=10.0`, já em
`backend/requirements.txt`) decodifica e valida a imagem de fato, não apenas a extensão/nome do
arquivo enviado pelo client. O backend então grava a imagem já validada em um bucket **público**
dedicado (`avatars`) do Supabase Storage — diferente do bucket privado `media` usado por mídia de
nota — porque avatares aparecem em muitas listagens (sugestões, comentários, moderadores) e não
faz sentido reemitir URLs assinadas de 1h para cada renderização de lista; não há dado sensível em
uma foto de perfil que o usuário escolheu tornar pública.

## Technical Context

**Language/Version**: Python 3.11 (Django + DRF backend), TypeScript/React 19 (Next.js 16 frontend)

**Primary Dependencies**: Django REST Framework, Pillow (already a dependency, image validation),
`supabase-py` storage client (already used in `apps.sync.media`), TanStack Query + shadcn/ui on
the frontend (already used in `frontend/src/app/account/page.tsx`)

**Storage**: Postgres via Supabase (new `avatar_path` column on `accounts.User`); Supabase Storage
new public bucket `avatars` for the image bytes (mirrors the existing `provision_media_bucket`
management command pattern, but `public: True`)

**Testing**: pytest (backend, `backend/apps/accounts/tests/`), Vitest/Playwright (frontend)

**Target Platform**: Web (Heroku-hosted Django backend, Next.js frontend) — no add-on changes;
avatar is a web-only surface, the add-on never touches profile images

**Project Type**: Web application (existing `backend/` + `frontend/` split)

**Performance Goals**: Avatar upload completes and reflects in UI within the SC-001 target
(<10s round trip for a typical profile photo, a few MB)

**Constraints**: Server MUST validate real image content (not just client-declared MIME/extension)
before persisting or serving; existing `name`-only edit path (`ProfileUpdateSerializer`,
`MeView.patch`) MUST keep working unchanged (FR-010/SC-005)

**Scale/Scope**: One new model field + 3 read paths (suggestions, comments, moderator list) that
already serialize an author/user and need an `avatar_url` added — no new tables beyond the
`avatar_path` column

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle III (LGPD by design)**: Avatar is user-supplied, optional, deletable (FR-011) —
  no new personal-data category beyond what the user explicitly chooses to publish. No consent
  gate needed (not marketing/research data use). **PASS**.
- **Principle IV (Secure by default)**: FR-002/FR-003 require real server-side validation
  (Pillow decode + re-encode, not trust client `Content-Type`), rejecting invalid files with a
  clear error and leaving prior state untouched. HTTPS already enforced platform-wide. **PASS**
  — addressed explicitly in Phase 1 design (data-model.md validation rules).
  - Public bucket for avatars is a deliberate scope decision, not a security gap: the content
    is a photo the user chose to publish as their public identity across the platform (same
    trust level as their display name), not sensitive data. Recorded as a design decision in
    research.md, not a violation.
- **Principle V (YAGNI / MVP scope discipline)**: No thumbnail/resize pipeline, no coupling
  between `target_career` and catalog filters — both explicitly out of scope per spec
  Assumptions, matching the PRD's non-goals discipline. **PASS**.
- **Principle VI (context7 + ponytail)**: Reuses the existing `apps.sync.media` signed-URL /
  bucket-provisioning pattern rather than inventing a new storage abstraction; multipart-to-Django
  is the simplest way to satisfy synchronous server-side validation (no two-step
  upload-then-validate-then-maybe-delete dance). **PASS**.
- **Principle VII (design pipeline)**: `/account` avatar upload UI and the three read surfaces
  (suggestion list, comment thread, moderator list) go through `ui-ux-pro-max` → `impeccable`
  before shipping, and must hold at 360px viewport (FR-053). Tracked as an implementation-phase
  gate, not a plan-time blocker.
- **Principle VIII (sync fidelity / Note Content vs Card State)**: Not applicable — this feature
  touches only `accounts.User` (a person's own profile), not notes, decks, or scheduling data.
  **N/A**.
- **Principle I (Parity over reinvention)**: No AnkiHub-specific precedent for a Brazilian-market
  avatar feature to mirror; reusing this project's own existing Supabase Storage conventions
  satisfies the spirit of the principle (don't invent a new pattern where one already exists in
  this codebase). **PASS**.
- **Principle II (Unidirectional sync)**: N/A — avatar/profile fields are never synced to the
  add-on's local Anki collection; they are a web-only profile attribute.

No violations requiring Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/007-profile-edit-avatar/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── accounts-api.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── accounts/
│   │   ├── models.py            # add User.avatar_path (nullable CharField)
│   │   ├── serializers.py       # ProfileUpdateSerializer gains target_career/target_board/
│   │   │                        # avatar write path; UserSerializer/PROFILE_FIELDS gains avatar_url
│   │   ├── views.py              # MeView.patch handles multipart avatar upload + validation
│   │   │                        # and avatar removal (FR-011)
│   │   ├── avatars.py            # NEW: Pillow validation + Supabase Storage upload,
│   │   │                        # mirrors apps/sync/media.py's role for the media bucket
│   │   └── migrations/           # new migration for avatar_path
│   ├── discussions/
│   │   └── serializers.py       # CommentSerializer gains avatar_url (via author)
│   ├── suggestions/
│   │   └── serializers.py       # Suggestion serializer gains avatar_url (via author)
│   └── catalog/
│       └── serializers.py       # DeckModeratorSerializer gains name + avatar_url (name was
│                                # missing entirely before this feature)
│   └── sync/management/commands/
│       └── provision_avatars_bucket.py  # NEW: mirrors provision_media_bucket.py, public bucket
└── tests/ (co-located per app, existing pytest layout)

frontend/
├── src/
│   ├── app/account/page.tsx     # avatar upload/remove control + target_career select +
│   │                            # target_board input, alongside existing name field
│   ├── components/               # shared Avatar display component (placeholder fallback),
│   │                            # used by suggestion list, comment thread, moderator list
│   └── lib/api-client.ts        # multipart upload helper if not already present
└── tests/ (existing Vitest/Playwright layout)
```

**Structure Decision**: Existing `backend/` (Django apps) + `frontend/` (Next.js) split, no new
top-level projects. Changes are additive within `apps/accounts`, `apps/discussions`,
`apps/suggestions`, `apps/catalog`, and `frontend/src/app/account` plus a small shared avatar
display component for the three read surfaces.

## Complexity Tracking

*No Constitution Check violations — table not needed.*
