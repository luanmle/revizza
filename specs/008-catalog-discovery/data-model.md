# Phase 1 Data Model: Descoberta avançada do catálogo

## Deck (modified)

| Field | Type | Change | Notes |
|---|---|---|---|
| `creator` | nullable reference to User | new | Historical original creator. Set on publish. Backfill from earliest root moderator where possible. If the user account is deleted, display creator as unavailable. |
| `is_official` | boolean | new | Defaults to false. Read-only for normal users and moderators; staff/admin-controlled. |
| `last_updated_at` | derived timestamp | new response field only | Latest content-update timestamp from deck notes, fallback to deck creation. Not stored for MVP. |
| `name`, `description`, `subject_tags`, `note_count`, `subscriber_count`, `created_at` | existing | unchanged | Still returned by catalog list/detail. |

## User summary (response shape)

Used for creator and active moderators.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID/string | Public user id for display context. |
| `name` | string | Profile display name; may be blank. |
| `avatar_url` | URL/null | Public avatar URL from existing avatar storage helper; frontend uses fallback initials when null. |

## DeckModerator (existing)

No schema change. Active moderators power the "Meus baralhos" tab and the moderator avatar list on
deck detail. Pending moderators do not count as "my decks" and are not displayed as active moderators.

## Subscription (existing)

No schema change. Active subscriptions power the "Inscritos" tab and remain compatible with add-on use
of the existing subscribed catalog query.

## Deck Discovery State (frontend/query state)

| Field | Values | Notes |
|---|---|---|
| `tab` | `catalog`, `moderated`, `subscribed` | Maps to no personal filter, `moderated=1`, or `subscribed=1`. |
| `tag` | string/empty | Existing tag filter, combinable with tab and sort. |
| `sort` | `recommended`, `popular`, `updated`, `notes`, `recent` | Defaults to `recommended`. |
| `cursor` | opaque string/null | Reset whenever tab, tag, or sort changes. |

## Validation and lifecycle

- `creator` is set during publish. Existing decks are backfilled best-effort from root moderators; if no
  source exists, the response returns `creator: null`.
- Removing a moderator does not clear `Deck.creator`.
- `is_official` defaults false for existing and new decks.
- Moderators cannot mutate `is_official` through deck edit/moderation flows.
- Public sort values outside the allowed set are rejected with a validation error or treated as default
  only if the API already uses defaulting consistently; tasks should choose one behavior and test it.
- Cursor is valid only for the exact same tab/tag/sort combination that created it.
