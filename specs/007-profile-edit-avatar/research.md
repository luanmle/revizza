# Phase 0 Research: Edição de Perfil (Foto e Dados Adicionais)

No open `NEEDS CLARIFICATION` markers remained in the Technical Context — this feature builds on
patterns already established in this codebase, so research is a targeted verification of those
patterns rather than open-ended exploration.

## Decision: Upload transport — multipart to Django, not client-direct presigned URL

**Decision**: Client sends the image as multipart form data directly to a Django endpoint
(`MeView.patch`, `multipart/form-data`). Django validates it synchronously, then uploads the
already-validated bytes to Supabase Storage using the existing service-role client
(`apps.sync.media._storage()` pattern).

**Rationale**: FR-002/FR-003 require rejecting invalid uploads (wrong type, oversized, corrupt)
*before* anything is persisted or exposed, with the prior avatar left untouched. The existing note
-media flow (`apps/sync/views.py`) uses a two-step presigned-URL handoff (backend issues a signed
upload URL, client PUTs bytes directly to storage, backend never sees the bytes) — that pattern
fits note media because the uploader there is always a verified deck moderator uploading
already-trusted content by content-hash. Profile avatars are uploaded by *any* authenticated user
through a public-facing form, so the "never trust client" bar is higher: the backend must actually
decode the file to confirm it is a real image before it can be shown to other users at all. A
presigned-URL flow would let an invalid/malicious file land in storage first and only be validated
(and deleted) after the fact — asynchronous validation for something synchronous by nature (FR-003:
"o avatar anterior... permanece inalterado" on rejection is trivial when nothing was ever uploaded
to storage on failure).

**Alternatives considered**:
- *Presigned URL, validate-then-delete-if-invalid*: rejected — adds a race window where an invalid
  file is briefly public, and adds cleanup-on-failure logic the multipart approach doesn't need.
- *Client-side validation only*: rejected outright — FR-002 explicitly requires server-side
  validation; matches Principle IV (Secure by default).

## Decision: Validation library — Pillow (already a dependency)

**Decision**: Use `PIL.Image.open()` + `.verify()`/`.load()` to confirm the upload is a decodable
raster image, check its format against an allowlist (JPEG, PNG, WebP), check file size against a
byte-size ceiling, and check pixel dimensions against a maximum before accepting.

**Rationale**: `Pillow>=10.0` is already in `backend/requirements.txt` (used elsewhere in the
project, e.g. any existing image handling) — no new dependency needed, satisfying Principle VI.
Decoding via Pillow catches files that merely *claim* to be an image (wrong magic bytes, truncated
data, disguised non-image payloads) which extension/`Content-Type` header checks alone would miss.

**Alternatives considered**:
- *`python-magic` / libmagic MIME sniffing only*: rejected — redundant with what Pillow's decode
  step already proves (a real image decodes; a fake one throws), would be a second dependency for
  a strictly weaker guarantee.
- *Trust file extension/`Content-Type`*: rejected — exactly the "never confide in client" gap
  FR-002 calls out.

## Decision: Storage bucket — new public `avatars` bucket, separate from `media`

**Decision**: Provision a second Supabase Storage bucket, `avatars`, created `public: True` (unlike
the existing private `media` bucket), via a new management command mirroring
`provision_media_bucket.py`. Avatar URLs are the bucket's public URL (no expiry), not a signed URL.

**Rationale**: The `media` bucket is private and fronted by 1-hour signed URLs because note media
(e.g. images embedded in flashcard fields) can be gated by subscription/moderation state. Avatars
are different: the user explicitly publishes them as their public identity, they must render
correctly on every page that lists suggestions/comments/moderators (potentially many at once), and
re-signing a URL per render for a list of avatars is unnecessary complexity and load for content
the owner already chose to make public. A separate bucket keeps the two lifecycles (moderated,
access-controlled note media vs. public profile identity) from sharing one bucket's ACL semantics.

**Alternatives considered**:
- *Reuse the `media` bucket with a signed URL per avatar render*: rejected — adds request
  overhead and TTL-expiry complexity (cached list pages would need re-signing) for content that
  doesn't need access control.
- *Store avatar bytes in Postgres*: rejected outright by the spec itself ("referência à imagem no
  storage, não o binário no banco").

## Decision: No thumbnail/resize pipeline in this version

**Decision**: Store the validated original (within a size/dimension ceiling), serve the same URL
everywhere; any visual downscaling for small contexts (e.g. a comment avatar vs. the account page)
is done via HTML/CSS sizing on the frontend, not server-generated variants.

**Rationale**: Matches the spec's own Assumption and Principle V (YAGNI) — no user story or
success criterion requires multiple resolutions; a single reasonably-capped image is sufficient
for every listed surface. Revisit only if a real performance problem (large original files slowing
list-heavy pages) is observed in practice.

**Alternatives considered**:
- *Generate thumbnail variants on upload*: rejected as premature — no measured need yet; upgrade
  path is documented so it's easy to add later without a data-model change (the same `avatar_path`
  could become a prefix for multiple derived sizes).

## Decision: `target_career`/`target_board` — plain profile metadata, no catalog coupling

**Decision**: `ProfileUpdateSerializer` accepts `target_career` (validated against
`User.TargetCareer.choices`, already defined) and `target_board` (free text, optional) as
additional writable fields alongside `name`. No change to `apps.catalog` filtering/recommendation
logic.

**Rationale**: Matches the spec's Assumption and keeps this feature's blast radius to
`apps.accounts` plus the three read surfaces — introducing a catalog-filter dependency on
`target_career` would be new, unrequested scope (Principle V).

**Alternatives considered**:
- *Auto-filter deck catalog by `target_career`*: rejected — out of scope per spec; no user story
  or acceptance scenario requests it.
