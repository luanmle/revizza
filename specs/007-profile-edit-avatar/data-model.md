# Phase 1 Data Model: Edição de Perfil (Foto e Dados Adicionais)

## Entity: `User` (extended — `backend/apps/accounts/models.py`)

Existing fields unchanged: `auth_id`, `email`, `name`, `target_career`, `target_board`,
`consent_marketing_emails`, `consent_research_data`, `is_suspended`, `deletion_requested_at`.

**New field**:

| Field | Type | Notes |
|---|---|---|
| `avatar_path` | `CharField(max_length=500, null=True, blank=True)` | Path within the `avatars` Supabase Storage bucket (e.g. `<user_id>/<content_hash>.<ext>`), mirroring `MediaFile.storage_path`'s role. `null`/blank = no avatar uploaded, frontend renders the default placeholder. |

No new table: one column is sufficient (mirrors how `apps/notes` `MediaFile.storage_path` is just
a string column, not a separate media-metadata model — there's no need for a metadata model here
since there's exactly one avatar per user, not a many-to-one collection).

**Validation rules** (enforced server-side in `apps/accounts/avatars.py`, never trusted from the
client):

1. **Format allowlist**: decoded image format (via `PIL.Image.open(...).format`) MUST be one of
   `JPEG`, `PNG`, `WEBP`. Anything else (including files that fail to decode at all) is rejected.
2. **Size ceiling**: raw upload size MUST NOT exceed 5 MB. Rejected uploads return a clear error
   naming the limit.
3. **Dimension ceiling**: decoded pixel dimensions MUST NOT exceed 4096×4096. Rejected uploads
   return a clear error naming the limit.
4. On any validation failure: nothing is written to storage or to `avatar_path`; the user's
   existing avatar (if any) is left exactly as it was (FR-003).
5. On success: the new image is uploaded to the `avatars` bucket at a path derived from the
   user's id and a content hash (so re-uploading identical bytes doesn't create duplicate objects);
   `avatar_path` is updated to point at it; the previous object at the old `avatar_path` (if
   different) is deleted from storage to avoid orphaned files.
6. **Removal** (FR-011): a request to clear the avatar sets `avatar_path` to `null` and deletes the
   corresponding storage object; the frontend falls back to the default placeholder.

**`target_career`**: unchanged choices (`fiscal`/`policial`/`juridica`/`outra`), now writable via
`ProfileUpdateSerializer` in addition to registration. Validated against `User.TargetCareer.choices`
by DRF's existing `ChoiceField`/model-field validation — no new validation code needed.

**`target_board`**: unchanged free-text `CharField(max_length=120, null=True, blank=True)`, now
writable via `ProfileUpdateSerializer`. Optional — blank/`null` is valid (Edge Case: usuário deixa
`target_board` em branco).

## Derived/read-only representation: `avatar_url`

Not a stored field — a `SerializerMethodField` (or equivalent) computed wherever a user is
serialized for display:

- `UserSerializer` (`apps/accounts/serializers.py`) — the user's own profile view.
- `CommentSerializer` (`apps/discussions/serializers.py`) — via `comment.author`.
- The suggestion serializer with `author_name` (`apps/suggestions/serializers.py`) — via
  `suggestion.author`.
- `DeckModeratorSerializer` (`apps/catalog/serializers.py`) — via `moderator.user`. This serializer
  currently exposes only `user_id`/`email` with **no `name` field at all**; this feature adds both
  `name` and `avatar_url` here, since User Story 2 / Acceptance Scenario 3 requires the moderator
  list to show the avatar next to the name.

Computation: if `avatar_path` is set, return the `avatars` bucket's public URL for that path
(no signing/expiry, per research.md); if not set, return `None` and let the frontend render its
default placeholder component (Edge Case: usuário sem avatar).

## State transitions

```
no avatar --(valid upload)--> has avatar (path A)
has avatar (path A) --(valid upload)--> has avatar (path B), path A deleted from storage
has avatar (path A) --(remove)--> no avatar, path A deleted from storage
any state --(invalid upload)--> unchanged (rejected before persistence)
```

## Relationships

No new relationships. `avatar_path` lives on the existing `User` row; `avatar_url` is derived at
serialization time wherever an existing FK to `User` (`Comment.author`, suggestion's author FK,
`DeckModerator.user`) is already being serialized.
