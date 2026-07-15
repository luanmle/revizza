# Phase 0 Research: Descoberta avançada do catálogo

## Decision 1: Keep one catalog endpoint with query parameters

**Decision**: Use the existing deck list endpoint for all discovery modes:
`subscribed=1`, `moderated=1`, `tag=<text>`, `sort=<value>`, and cursor pagination.

**Rationale**: The existing list already owns catalog filtering and is consumed by both web and add-on.
Adding separate endpoints would duplicate pagination, tag filtering, serializer fields, and empty-state
logic.

**Alternatives considered**:
- New `/my-decks/` endpoint: rejected; same resource and same pagination rules.
- Client-side filtering after fetching catalog: rejected; wrong for pagination and leaks incomplete
sets.

## Decision 2: Use a safe sort mapping, not raw ordering exposure

**Decision**: Accept only these public sort values: `recommended`, `popular`, `updated`, `notes`,
`recent`. Map each to a fixed ordering tuple with a final stable tie-breaker.

**Rationale**: Context7 DRF docs confirm `CursorPagination.ordering` controls cursor order and
`OrderingFilter` should restrict exposed fields. A fixed mapping avoids exposing raw model fields while
keeping cursor order deterministic.

**Alternatives considered**:
- DRF `OrderingFilter` with arbitrary `ordering`: rejected; too much public surface and easier to make
unstable.
- Sort only in frontend: rejected; pagination would be wrong across pages.

## Decision 3: Store creator explicitly on Deck

**Decision**: Add `Deck.creator` as nullable reference to the original creator user, set during publish
and backfilled from the oldest active/root moderator when possible.

**Rationale**: The spec requires creator to remain historical if the creator stops moderating. The
current implicit source is a moderator relation that can be removed, so it cannot satisfy that rule.
Referencing the user avoids duplicating personal data snapshots.

**Alternatives considered**:
- Keep deriving creator from oldest moderator with no inviter: rejected; removal loses history.
- Store creator name/avatar snapshot: rejected; worse for privacy and stale profile data.

## Decision 4: Derive last_updated_at from Note.mod

**Decision**: Annotate list/detail with the latest note content timestamp for the deck, falling back to
deck creation when no notes exist.

**Rationale**: `Deck.updated_at` changes for deck metadata and not all content changes. `Note.mod` is
already the domain timestamp used by sync/content changes, so it matches user meaning: "conteúdo mudou".

**Alternatives considered**:
- Use `Deck.updated_at`: rejected; does not represent note changes reliably.
- Store denormalized `last_updated_at`: rejected for MVP; annotation is simpler until catalog size proves
otherwise.

## Decision 5: Official badge is admin/staff-only metadata

**Decision**: Add `Deck.is_official` default false and expose it read-only to web/API consumers; staff
sets it through the administrative path, not through moderator deck flows.

**Rationale**: Official means platform curation, not self-certification. No public write endpoint is
needed for MVP.

**Alternatives considered**:
- Moderator-controlled flag: rejected; destroys trust signal.
- New public staff endpoint: rejected; Django admin already exists for staff-only moderation actions.

## Decision 6: Use existing product UI primitives

**Decision**: Use existing shadcn primitives already installed (`tabs`, `select`, `badge`, `skeleton`)
and `UserAvatar`; keep layout restrained, dense, and mobile-first per design system.

**Rationale**: This is a product surface, not a marketing page. Existing components cover the need.

**Alternatives considered**:
- Custom tab/select/avatar components: rejected; duplicates available UI.
- Persist sort preference: rejected; not required by spec and adds account state.
