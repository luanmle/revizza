# API Contract: Profile Edit (Avatar + Career Metadata)

Extends the existing `accounts` endpoints. Trailing-slash routes and error-shape conventions match
existing endpoints in this project (Principle I).

## `GET /accounts/me/` (existing, response shape extended)

Response body gains one field:

```json
{
  "id": "...",
  "name": "...",
  "email": "...",
  "avatar_url": "https://.../storage/v1/object/public/avatars/<path>" ,
  "target_career": "fiscal",
  "target_board": "...",
  "consent_marketing_emails": false,
  "consent_research_data": false,
  "deletion_requested_at": null,
  "created_at": "..."
}
```

`avatar_url` is `null` when no avatar has been uploaded.

## `PATCH /accounts/me/` (existing, request shape extended)

Two ways to call this endpoint depending on what's being changed — both partial, both may be
combined with the existing `name` field:

### a) Text fields (JSON body, unchanged content type)

```json
{
  "name": "...",
  "target_career": "policial",
  "target_board": "TJ-SP"
}
```

- `target_career` MUST be one of `fiscal`/`policial`/`juridica`/`outra` or omitted/`null`.
- `target_board` is free text, may be blank/omitted.
- Behaves exactly as today for `name`-only requests (FR-010, no regression).

**Response**: `200 OK` with the full updated `UserSerializer` body (as in `GET /accounts/me/`).

**Errors**: `400` with field-level messages on invalid `target_career` choice (DRF default
`ChoiceField` validation error shape — no new error format introduced).

### b) Avatar upload (`multipart/form-data`)

```
PATCH /accounts/me/
Content-Type: multipart/form-data

avatar: <file bytes>
```

- Server decodes the file with Pillow, validates format (JPEG/PNG/WebP), size (≤5MB), and pixel
  dimensions (≤4096×4096) per data-model.md.
- **Success**: `200 OK`, updated `UserSerializer` body with the new `avatar_url`. Previous storage
  object (if any) is deleted server-side.
- **Failure** (bad format/oversized/corrupt/undecodable): `400 Bad Request`,
  `{"avatar": ["<human-readable reason, e.g. 'Formato de imagem não suportado.'>"]}`. No change to
  the user's existing `avatar_path`/`avatar_url` (FR-003).

### c) Avatar removal

```json
{
  "avatar": null
}
```

- **Response**: `200 OK`, `avatar_url` becomes `null`. Storage object deleted server-side (FR-011).

## Read surfaces gaining `avatar_url` (no route changes, response shape extended)

- `GET /suggestions/...` (existing list/detail endpoints in `apps.suggestions`) — each suggestion's
  author representation gains `avatar_url` alongside the existing `author_name`.
- `GET /discussions/...` (existing comment endpoints in `apps.discussions`) — `CommentSerializer`
  gains `avatar_url` alongside `author_name`.
- `GET /catalog/decks/<id>/moderators/` (`DeckModeratorListCreateView`) — `DeckModeratorSerializer`
  gains `name` (previously absent) and `avatar_url` alongside the existing `user_id`/`email`.

All three: `avatar_url` is `null` when the author/moderator has no avatar — frontend renders the
default placeholder, never a broken image link (Edge Case, Acceptance Scenario US2.4).
