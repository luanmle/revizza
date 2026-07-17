# Phase 1 Data Model: Hardened Add-on Media Sync

## Entities

### MediaFile (existing, `backend/apps/notes/models.py`) — modified

Represents one deduplicated media object belonging to a deck.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID (from `BaseModel`) | unchanged |
| `deck` | FK → `catalog.Deck`, `related_name="media_files"` | unchanged |
| `content_hash` | `CharField(max_length=64)` | unchanged — SHA-256 hex digest |
| `storage_path` | `CharField(max_length=500)` | unchanged — `f"{deck.id}/{content_hash}"` |
| `original_filename` | `CharField(max_length=255)` | unchanged — retained for display/extension derivation only; **no longer used as the add-on's local filename** (see FR-011 / research.md §2) |
| `status` | **new** `CharField(max_length=20, choices=STATUS_CHOICES, default="ready")` | `pending_upload` \| `ready`. New rows from a fresh publish start `pending_upload`; flips to `ready` via the confirm endpoint (research.md §7). Existing rows backfilled to `ready` (research.md §8). |

**Constraints** (unchanged): `unique_media_hash_per_deck` on `(deck, content_hash)`.

**State transitions**:

```
[row created by PublishView, new hash]  →  pending_upload
        │
        │  POST .../media/{hash}/confirm/  (idempotent)
        ▼
       ready
```

There is no `ready` → `pending_upload` transition (once confirmed, a `MediaFile` stays `ready` for its lifetime under this feature — a genuinely corrupted/missing Storage object is an operational/support concern, not a state this feature models).

**Validation rules**:
- `status` MUST default to `ready` at the migration/backfill level for pre-existing rows (research.md §8) — this is a one-time data migration default, not an app-level validation rule.
- A `MediaFile` MUST NOT be included in any delta/full/publish-echo `media` manifest list while `status = pending_upload` (FR-005) — enforced in `_deck_payload` (`apps/sync/views.py`) via a queryset filter, not a model-level constraint.
- `MediaDownloadView` MUST return 404 (not the signed URL) for a hash whose only matching `MediaFile` is `pending_upload` and the requester is not its uploader — see contracts/media-sync.md for the exact response shape.

### Media manifest item (wire shape, delta/full/publish payloads) — unchanged shape

```json
{"filename": "<original_filename, display-only>", "content_hash": "<sha256 hex>"}
```

No new fields on the wire; the shape is identical to today. The semantic change is entirely server-side (which rows populate this list — `ready` only).

### Staged media (add-on-local, in-memory/temp-file only, not a persisted model)

A transient value used only within one sync/publish run:

| Field | Type | Notes |
|---|---|---|
| `content_hash` | str | from manifest |
| `staging_path` | `pathlib.Path` | temp file under `user_files/media_staging/`, deleted after commit or failure |
| `resolved_filename` | str | `f"{content_hash}.{ext}"` — the deterministic local filename (research.md §2) |
| `byte_size` | int | measured during streamed download, must be ≤ 10 MB |

Never persisted to the local peewee state DB (`db/models.py::SyncStateCache`) or to any file outside the staging directory and (on success) the collection's own media folder.

## Relationships

```
Deck 1───* MediaFile (existing)
Note  *───* MediaFile   (implicit, via <img src> references inside Note.field_values —
                          no explicit FK exists today and none is added by this feature;
                          the association is resolved by content-hash string matching at
                          sync time, exactly as it is today)
```

No new relationships are introduced. The Note↔MediaFile association remains implicit (HTML string reference), consistent with the existing design and with Anki's own native model (Anki doesn't have a notes↔media join table either — it's discovered by scanning field HTML, which is exactly what `col.media.files_in_str` and the backend's field-scan in `build_publish_payload` already do).

## Note Content vs. Card State (Constitution Principle VIII)

Everything in this data model — `MediaFile`, the manifest, staged media, and the `<img src>` rewrite performed at apply time — is Note Content: it changes what a field's HTML string contains and what files sit in the media folder. Nothing here reads or writes `cards`, `revlog`, deck-options scheduling settings, or any `col.sched` API. The FR-011 filename rewrite is applied via the same `_fill_fields`-adjacent field-value mutation path that already exists for ordinary field-content sync (`main/sync.py::_fill_fields`), before `col.update_note`/`col.add_note` — never via a card-level API call. See `contracts/media-sync.md` for the explicit test obligation this creates.
