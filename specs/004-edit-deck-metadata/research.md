# Phase 0 Research: Edição de título/descrição/tags do deck

## Decision 1: Endpoint shape

**Decision**: `PATCH /api/v1/decks/{id}/` on the existing `DeckDetailView`
(`backend/apps/catalog/views.py`), adding a `patch` method restricted to active moderators. Accepts
partial payload (`name`, `description`, `subject_tags` — any subset).

**Rationale**: `DeckDetailView` already owns `GET /decks/{id}/`; adding `PATCH` to the same resource
matches REST convention and the existing trailing-slash routing (Principle I) without a new URL.

**Alternatives considered**: A separate `PUT /decks/{id}/metadata/` endpoint — rejected, adds a URL
for no behavioral gain over `PATCH` on the existing resource.

## Decision 2: Authorization check

**Decision**: Reuse the inline active-moderator check already used by
`DeckModeratorListCreateView.post` and `DeckModeratorRemoveView.delete` — a direct
`DeckModerator.objects.filter(deck=deck, user=request.user, status=ACTIVE).exists()` guard inside the
view, returning `403` with a Portuguese `detail` message on failure.

**Rationale**: This is the codebase's established pattern for this exact permission shape (a
per-deck moderator check that can't be expressed as a static DRF permission class without passing the
deck through view kwargs). Introducing a new `IsActiveModerator` permission class for a single call
site would be one abstraction for one use — against Principle VI (minimal code).

**Alternatives considered**: A shared DRF `BasePermission` subclass — deferred; revisit only if a
third view needs the identical check (currently only invite/remove/this one; if a 4th appears, promote
to a shared permission class).

## Decision 3: Sanitization of `description`

**Decision**: Reuse `apps.notes.sanitize.sanitize_html` (nh3-based, existing allowlist) unchanged for
the `description` field.

**Rationale**: Constitution Principle IV already mandates one sanitization policy for user-submitted
HTML; the deck description is the same class of risk (persisted HTML rendered to other users) as note
fields, so it gets the same allowlist rather than a second one.

## Decision 4: Keeping `name` edits from renaming the local Anki deck (FR-006)

**Problem found during research**: `backend/apps/sync/views.py::_deck_payload` currently sends
`deck_name: deck.name` in every sync/full-resync payload, and the add-on's sync handler
(`addon/ankihub_br/main/sync.py`) calls `col.decks.id(payload["deck_name"])`, which **creates or
looks up a local deck by that exact name**. If `name` were edited on the web and fed straight into
this payload, the next sync would silently create/move the user's local deck under the new name —
exactly the surprise FR-006 forbids, and a real conflict between "make `name` editable" and "don't
touch the local Anki deck."

**Decision**: Add a new `Deck.anki_deck_name` field, set once from `data["name"]` at publish time
(`PublishView.post`) and never touched by the new edit endpoint. `_deck_payload` reads
`deck.anki_deck_name` instead of `deck.name` for the `deck_name` key it sends to the add-on. The
catalog-facing `name` (list/detail serializers, the new edit endpoint) becomes freely editable and
decoupled from what the add-on uses to place the local deck.

**Rationale**: This is the minimal change that actually satisfies FR-006 — without it, FR-006 would be
a documentation-only promise contradicted by existing sync code. A single immutable snapshot field is
simpler than versioning or migrating the local deck path, and requires no add-on changes.

**Migration note**: Backfill `anki_deck_name = name` for all existing decks in the same migration that
adds the column (default value = current `name`), so already-published decks keep syncing to their
current local deck path unchanged.

**Alternatives considered**:
- Let `name` edits propagate to `deck_name` in sync payloads and have the add-on rename the local deck
  to match — rejected by FR-006 explicitly (surprise/scope risk called out in the original request).
- Version/rollback the local deck path — rejected, over-engineered for a single flat rename scenario
  (YAGNI).

## Decision 5: Frontend edit surface

**Decision**: New `frontend/src/app/decks/[id]/edit/page.tsx`, linked from the deck detail page only
when `is_moderator` is true (same signal `DeckDetailSerializer.get_is_moderator` already exposes),
mirroring the existing `moderators/page.tsx` moderator-only page pattern.

**Rationale**: Matches an established sibling page's visibility convention (Principle VI: reuse over
reinvention); no new authorization concept needed on the frontend since the backend is the actual gate.
