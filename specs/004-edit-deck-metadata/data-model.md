# Phase 1 Data Model: Edição de título/descrição/tags do deck

## Deck (modified)

Existing model, `backend/apps/catalog/models.py`. One field added.

| Field | Type | Change | Notes |
|---|---|---|---|
| `name` | `CharField(max_length=200)` | unchanged, now editable | Catalog display title (FR-001). Must not be blank after edit (FR-003). |
| `description` | `TextField(blank=True)` | unchanged, now editable | Rich text HTML, sanitized server-side via `sanitize_html` before save (FR-005). |
| `subject_tags` | `JSONField(default=list)` | unchanged, now editable | List of strings; normalized (dedup, drop empties) or rejected if not a list of strings (FR-008). |
| `anki_deck_name` | `CharField(max_length=200)` | **new** | Immutable snapshot of `name` at publish time. Used only by `apps/sync/views.py::_deck_payload` as the `deck_name` sent to the add-on. Never updated by the edit endpoint (FR-006). Migration backfills `anki_deck_name = name` for existing rows. |

No changes to `DeckModerator`, `Subscription`, `Note`, `NoteType`, or any other model. No Card State
(scheduling) entity is touched — this feature is Deck-level catalog metadata only (Constitution
Principle VIII).

## Validation rules (edit endpoint)

- `name`: required if present in payload; if present, must be a non-empty string after trimming.
- `description`: optional; any string accepted, sanitized via `sanitize_html` before persisting.
- `subject_tags`: optional; must be a list of strings if present; server dedupes and drops
  empty/whitespace-only entries before saving.
- Partial payload allowed: only fields present in the request body are touched (FR-007); absent fields
  keep their current value.

## State / lifecycle

No new lifecycle — `Deck` rows already exist post-publish. This feature only adds a write path for
three already-existing fields plus the new immutable `anki_deck_name` snapshot captured once at
publish and never mutated afterward.
