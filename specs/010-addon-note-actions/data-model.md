# Phase 1 Data Model: Add-on Note Actions & Sync Stability

This feature adds **no backend tables or columns**. It adds one column to the add-on's local sync cache and reuses existing `Note` / `Suggestion` entities unchanged. Card State (scheduling) is never modeled here (Principle VIII).

## Backend (Postgres via Supabase) — unchanged

- **`Note`** (`apps/notes/models.py`) — reused as-is. Relevant fields: `id` (UUID, platform note id), `guid` (CharField, stable Anki GUID; unique per deck), `deck` (FK), `field_values` (JSON), `tags`. The GUID is the resolution key for the new redirect/resolve endpoints. No new field.
  - Existing constraint `unique_note_guid_per_deck` (deck, guid). Resolution by GUID alone assumes GUID uniqueness across decks in practice (Anki GUIDs are collision-safe); the resolver returns the single matching non-deleted note, or 404.
- **`Suggestion`** / **`SuggestionTargetNote`** (`apps/suggestions/models.py`) — reused as-is. A from-Anki change suggestion creates the same `Suggestion(type=CHANGE, author, deck, category, justification, …)` + one `SuggestionTargetNote`. No new type, flag, or column distinguishes origin.

## Add-on local cache (SQLite in `user_files/`) — one new column

**`SyncStateCache`** (`addon/ankihub_br/db/models.py`), primary key `(deck_id, note_id)` where `note_id == guid`:

| Field | Type | Existing? | Purpose |
|-------|------|-----------|---------|
| `deck_id` | Char | existing | owning Revizza deck id (also enables reverse `deck_id_for_guid`) |
| `note_id` | Char | existing | note GUID |
| `last_seen_mod` | DateTime | existing | delta cursor (`?since_mod=`) |
| `last_update_type` | Char | existing | created / updated / deleted |
| **`field_hash`** | **Char (nullable)** | **NEW** | stable hash of the note's Note-Content field values at last sync; baseline for the offline "nada a sugerir" pre-check (FR-008) |

- **Population**: set during note application in `main/sync.py` (where full field values are available), passed into `record_synced_notes`. `deleted` items store `field_hash = NULL`.
- **Migration**: peewee has no migration framework here; add the column defensively (e.g. `ALTER TABLE ... ADD COLUMN field_hash` guarded by a "column exists" check, or recreate) in `init_db`. `ponytail:` a NULL `field_hash` simply means "no baseline yet → fall through to the server `is_noop` backstop", so a lazy additive migration is safe.
- **Domain**: `field_hash` is Note Content only. It never stores or derives from ease/interval/due/review data (Principle VIII). It lives outside `collection.anki2` and is never sent to the backend.

## Derived / transient shapes (not persisted)

- **Note resolution result** (JSON from `GET /notes/resolve/?guid=`): `{ "note_id": UUID, "deck_id": UUID, "web_url": str, "history_url": str }` — see contracts/note-resolve.md.
- **Local diff decision** (in-memory): `hash(current_fields) == field_hash` → `no_change`; else → open suggestion dialog.

## Validation rules

- Resolver: `guid` must match one non-deleted `Note`; else 404.
- From-Anki suggestion: `category` and `justification` required (same serializer validation as web); server `is_noop` rejects empty changes; HTML sanitised server-side (unchanged).
- Public reads: no auth required for `NoteDetailView` / note-filtered `DeckSuggestionListView`; every write path keeps its existing auth + subscription checks.

## State transitions

None new. A from-Anki suggestion enters the existing `Suggestion` lifecycle (pending → accepted/rejected) identically to a web suggestion; acceptance feeds the existing sync queue. Sync application transitions Note Content only; Card State has no transition owned by this feature.
