# Phase 0 Research: Hardened Add-on Media Sync

No `NEEDS CLARIFICATION` markers remain in Technical Context — both spec-level clarifications (max file size, confirm-call granularity) were resolved in `/speckit-clarify`. This document resolves the remaining implementation-level unknowns needed before Phase 1 design.

## 1. Safe local media write primitive

**Decision**: Route every downloaded media file through `col.media.write_data(desired_fname, data)` (never `Path.write_bytes()` / raw filesystem writes into the media directory).

**Rationale**: Verified directly in the installed `anki` package source (`anki/media.py:97-101`, `uv` environment used by `addon/`):

```python
def write_data(self, desired_fname: str, data: bytes) -> str:
    """Write the file to the media folder, renaming if not unique.
    Returns possibly-renamed filename."""
    return self.col._backend.add_media_file(desired_name=desired_fname, data=data)
```

This routes through the Rust backend, which resolves the write strictly inside the media folder (no path-traversal regardless of `desired_fname` content) and **renames on collision instead of overwriting**. `add_file(path)` is a thin wrapper (`write_data(basename(path), open(path,'rb').read())`) — not used directly here since bytes are already in memory after download/validation.

**Alternatives considered**:
- Sanitize the filename ourselves (strip `..`, separators) and write with `Path.write_bytes()`. Rejected: reimplements a hostile-input parser that the platform already gets right; every additional hand-rolled sanitizer is a new place to get it subtly wrong (ponytail: reuse platform-native validation over custom parsing).
- Use `col.media.add_file()` (path-based). Rejected: would require writing the validated bytes to a temp file, then having `add_file` read them back — `write_data` takes bytes directly, one fewer disk round-trip, and the staging temp file (see §3) is for validation, not for handing off to Anki's API.

## 2. Collision handling: deterministic hash-based filenames vs. relying on Anki's rename-on-collision

**Decision**: The add-on derives its own local filename from the content hash before writing (`<sha256>.<ext>`), rather than passing the server's `original_filename` to `write_data` and living with whatever renamed result comes back.

**Rationale**: `write_data`'s rename-on-collision (`figura1.png` → `figura1 (1).png`) is byte-safe (never overwrites) but is **non-deterministic across syncs and across profiles** — the resulting filename depends on what else happens to already exist locally at write time. Two problems follow if the add-on used the server filename directly:
1. The exact same deck synced fresh on two different machines could end up with different local filenames for the same image (one machine already had an unrelated `figura1.png`), breaking reproducibility.
2. Every collision requires rewriting the note's `<img src>` to match whatever name Anki assigned — reactive, per-machine, and only discoverable after the write already happened.

Deriving the filename from the content hash up front makes the local name a pure function of content, identical across every profile and every deck, and lets the add-on rewrite `<img src>` **before** committing the note (single deterministic pass, not a reactive fixup). It also makes User Story 2's guarantee (two decks, same original name, different content → both survive) trivially true: different content → different hash → different filename, no reliance on collision-avoidance renaming at all. `write_data`'s rename-on-collision remains as a defense-in-depth backstop (it cannot be bypassed even if a filename derivation bug ever produced a clash), not the primary mechanism.

**Alternatives considered**:
- Keep server-supplied filenames, rewrite `<img src>` reactively based on `write_data`'s return value. Rejected per above (non-deterministic, reactive, extra bookkeeping to map "attempted name" → "actual name" per note).
- Namespace by deck (`<deck_id>/<filename>`). Rejected: Anki's media folder is flat by design (no subfolders); would require encoding the deck id into the filename anyway, which is strictly worse than a content hash for both determinism and collision-freedom (two decks could still coincidentally use identical `deck_id + filename` combos in theory, whereas content hash collisions are cryptographically negligible).

**Filename format**: `{content_hash}.{ext}`, where `ext` is derived from the server-supplied `original_filename`'s extension after stripping anything unsafe (`col.media.strip_illegal`/backend-side validation on write handles the rest). If the original had no extension, no extension is appended — Anki tolerates extension-less media filenames (regex-matched by `<img src>` either way).

## 3. Staging area for in-flight downloads

**Decision**: Downloads land in a temp file under Python's standard `tempfile` (e.g., `tempfile.NamedTemporaryFile(dir=<add-on user_files>/media_staging, delete=False)`), validated fully (size, hash, completeness) while still in that temp location, and only ever handed to `col.media.write_data` (bytes read from the validated temp file) after all checks pass. The temp file is deleted immediately after (success or failure).

**Rationale**: Directly implements FR-014 ("no partially-downloaded content may ever be reachable under a file's final resolved name") without inventing new infrastructure — `tempfile` is stdlib, and placing the staging directory under the add-on's own `user_files/` (already used by the local peewee state DB per `db/models.py`) keeps it on the same filesystem/volume as the rest of the add-on's local state, avoiding cross-device rename issues, and keeps it wholly separate from Anki's own `collection.media/` folder so a crash mid-download can never leave debris there for `col.media.check()` to trip over.

**Stale-file sweep (FR-015)**: At the start of each media sync run, before downloading anything new, delete any file already present in the staging directory older than one sync-run's worth of time (reuse `MIN_SYNC_INTERVAL_SECONDS`-scale reasoning — anything still there from a previous run is, by definition, orphaned since a completed run always cleans up after itself).

**Alternatives considered**:
- Stream directly into `col.media` via a partial/temp name inside `collection.media/` itself (e.g., `figura.png.part`), then rename on completion. Rejected: `collection.media/` is scanned/checksummed by Anki's own media-check machinery; introducing foreign `.part` files there risks tripping "unused media" or "missing media" warnings in Anki's native media check UI, which is an avoidable UX regression the constitution's YAGNI principle argues against introducing.
- In-memory buffering only (no disk temp file), validate in RAM, then write. Rejected as the default: works fine under the 10 MB cap (small enough to hold safely in memory), but a temp-file-on-disk approach is what makes the "abort before full body is buffered" requirement (FR-009b, oversized detection) cheap to implement uniformly via streamed writes with a byte-count guard, and generalizes without a rewrite if the size cap is ever revisited. (Implementation MAY buffer in memory up to the 10 MB cap in practice — `tempfile.SpooledTemporaryFile` gives both behaviors for free — this is a task-level detail, not a Phase 0 architectural decision.)

## 4. Background execution pattern (FR-017)

**Decision**: Reuse the existing `QueryOp(parent=mw, op=..., success=...).failure(...).run_in_background()` pattern already used in `gui/__init__.py::_run_network` and `gui/editor.py`, split into two sequential phases:

1. **Network/staging phase** — `QueryOp(...).without_collection().run_in_background()`: fetches delta/full JSON, protection info, and downloads+validates all media referenced by the manifest into the staging area (§3). Touches no `col` object at all.
2. **Apply phase** — a second `QueryOp` (collection given to the `op` callback, i.e. *not* `.without_collection()`) that runs the existing `apply_delta`/`apply_full` note-type/note/subdeck application, commits staged media via `col.media.write_data`, rewrites `<img src>` references, and on any failure restores the pre-sync backup — exactly the existing `sync_decks` responsibility, just now guaranteed to run off the Qt main thread and only after all media for that run already passed validation.

Both phases are chained from `sync_all` (currently synchronous end-to-end on whatever thread calls it — today the Qt main thread for the manual-menu and profile-open triggers). `sync_all` becomes the orchestrator that kicks off phase 1, and phase 1's `success` callback kicks off phase 2; only the final UI feedback (`tooltip(...)`) runs back on the main thread via `QueryOp`'s `success` callback semantics (already how `_run_network` works today).

**Rationale**: This is the only background-execution primitive already established in this codebase (verified in `gui/__init__.py:101-110` and `gui/editor.py:188-220` before writing this plan, per Principle VI) — no new dependency, no new concurrency primitive. Splitting network from collection-mutation is required by spec (FR "separate, when compatible with the verified APIs, the network step from the step that changes the collection") and additionally is what makes hash-derived-filename rewriting (§2) sequence correctly: all media must be validated and their final filenames known *before* note field values are written, which requires staging to complete before `apply_delta`/`apply_full` run — a strict reordering versus today's code (which applies notes, *then* syncs media afterward).

**Publish-side responsiveness (User Story 4, publish path)**: `publish_initial_deck` (currently synchronous, called from whatever UI action triggers "Criar deck Revizza" / republish attempt) gets the same treatment — the network-bound `upload_signed_media` + per-file confirm calls run inside a `QueryOp(...).without_collection()` (no collection mutation happens during publish's media step at all; the collection was already read to build the payload before this phase starts).

**Alternatives considered**:
- `CollectionOp` (Anki's undo-integrated background-op helper). Rejected: `CollectionOp` is designed for a single undoable collection mutation with automatic undo-stack integration; this feature's collection mutation (delta/full apply) already has its own custom backup/restore mechanism (`main/backup.py`) purpose-built for multi-step, multi-deck runs — layering `CollectionOp`'s undo semantics on top would be redundant complexity the constitution's minimal-code principle argues against, not a correctness improvement.
- Threading module directly (`threading.Thread`). Rejected: bypasses Anki's own background-task lifecycle management (cancellation, progress dialog wiring, ensuring collection access is serialized) that `QueryOp` already provides and that the rest of the codebase already relies on — reinventing it is exactly the kind of custom infrastructure Principle V/VI argue against.

## 5. Streaming download with size cap enforcement

**Decision**: `AnkiHubBrClient.download_file` switches from `requests.get(url, timeout=...)` (buffers the whole body unconditionally) to `requests.get(url, timeout=..., stream=True)`, checks `Content-Length` against the 10 MB cap up front when present (fast rejection), and additionally counts bytes while iterating `response.iter_content(chunk_size=...)` — aborting (closing the connection, discarding what was read) the moment the running total exceeds 10 MB even if `Content-Length` was absent or lied.

**Rationale**: `Content-Length` is a declared value, not a guarantee — a compromised or misbehaving Storage response could omit it or understate it. Streaming with a running byte-count guard is the standard, stdlib/`requests`-native way to enforce a hard cap without trusting the header (`requests`' own docs recommend `iter_content` for exactly this). No new dependency: `requests` is already a direct dependency of `ankihub_br_client`.

**Alternatives considered**: Trust `Content-Length` only, reject after-the-fact if actual body size differs. Rejected: a lying/missing header would let an oversized body be buffered in full before rejection, defeating the point of the cap as a DoS/resource-exhaustion guard (FR-009's explicit "aborted before the full body is buffered/written").

## 6. Retry/backoff policy for media downloads

**Decision**: Reuse `AnkiHubBrClient`'s existing `requests.Session` (mounted `HTTPAdapter` with `Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504], respect_retry_after_header=True)`) for the signed-URL download itself, since `download_file` already issues its GET through a plain `requests.get` today but the manifest-hash→signed-URL resolution (`get_media_url`) already goes through the retrying session. Extend `download_file` to also issue its GET through `self.session` (instance method, not a bare module-level `requests.get`) so the same retry/backoff/`Retry-After` policy applies uniformly to both legs of a media fetch.

**Rationale**: One retry policy, defined once, already correctly configured (transient-only: 429/5xx, honors `Retry-After`) — duplicating a second ad hoc retry loop for the Storage GET specifically would violate minimal-code discipline and risks the two policies drifting apart over time. Signed Storage URLs don't need the `Authorization` header (already true today, preserved), and the shared session's retry adapter operates purely on the HTTP layer, independent of headers sent.

**Alternatives considered**: A separate, smaller retry policy for Storage (e.g., fewer attempts, since a signed URL has a fixed TTL and repeated retries against an expired URL are pointless). Considered but rejected for this increment — expired-URL detection is a distinct concern (a 403/404 from Storage on an expired signed URL is *not* in `status_forcelist`, so the shared retry policy correctly does *not* retry it; that case is instead handled by the add-on re-requesting a fresh signed URL from `get_media_url`, per spec Edge Cases).

## 7. Backend: upload-confirmation contract shape

**Decision**: `POST /api/v1/decks/{deck_id}/media/{content_hash}/confirm/`, authenticated as the deck's creator/moderator (same authorization class as `PublishView`), called once per successfully uploaded file immediately after that file's `upload_signed_media` succeeds (per `/speckit-clarify` answer). Flips the matching `MediaFile.status` from `pending_upload` to `ready`. Idempotent (confirming an already-`ready` file is a no-op 200, not an error) so a retried publish attempt can safely re-confirm without needing to track what it already confirmed in a prior crashed attempt.

**Rationale**: Matches the clarified per-file granularity exactly. A dedicated route (rather than overloading `PublishView`'s response) keeps `PublishView` itself unchanged in shape (still returns `media_upload_urls` for whatever hashes are `pending_upload`), preserving contract backward-compatibility per `contracts/sync.md`'s existing versioning stance. Idempotency is required for FR-004 (resumable publish) — a crash between upload and confirm on a prior attempt must not make a retried confirm call fail.

**Alternatives considered**: A single batch confirm at the end of publish. Rejected by the `/speckit-clarify` decision (per-file confirm was explicitly chosen for its superior crash-resumability).

## 8. `MediaFile` status values & default for existing rows

**Decision**: `status = CharField(choices=[("pending_upload", ...), ("ready", ...)], default="ready")`. The migration backfills existing rows to `ready` (they were already being served successfully before this feature; treating them as anything else would be a regression, and the spec's Assumptions section already rules out retroactive migration of old media). Only newly created `MediaFile` rows (from a publish happening after this feature ships) start at `pending_upload` and require an explicit confirm call to reach `ready`.

**Rationale**: Directly matches the spec's documented Assumption (no retroactive migration) while still closing the actual gap (new publishes can no longer leak an unconfirmed URL).

**Alternatives considered**: Backfill existing rows to `pending_upload` and require confirmation retroactively. Rejected: spec explicitly rules this out, and it would immediately break every currently-working synced deck's media downloads until someone manually re-confirmed each row — a self-inflicted regression with no offsetting benefit.

## 9. Partial media-failure semantics within one deck's delta (resolves `/speckit-analyze` finding F1)

**Decision**: A single media item's validation/download failure does **not** raise an exception that aborts the whole deck's `apply_delta`/`apply_full` and triggers `main/backup.py`'s full restore. Instead, `stage_media` (§3, research T010) returns a *partial* `content_hash → resolved_filename` map covering only the items that validated successfully; any `<img src>` reference whose hash isn't in that map is left exactly as-is (untouched, unresolved) when `_fill_fields`/`_apply_notes` writes that note's fields — the note itself still commits normally. `main/backup.py`'s existing all-or-nothing restore-on-exception is preserved **unchanged** and continues to fire only for genuine collection-mutation errors (a raised exception during `apply_delta`/`apply_full` itself), not for a media item that simply didn't validate.

**Rationale**: This is the literal reading of FR-012 ("only the notes whose rendering depends on [the failed item]... flagged as incomplete") and the matching Edge Case ("the add-on must leave the field text untouched and skip only that reference, without failing the whole note/delta") — both describe a *skip*, not a *rollback*. Modeling it as "leave the reference unresolved" rather than "abort and restore" is also the only reading compatible with the plan's explicit "`backup.py` — unchanged" decision (plan.md Project Structure): no new partial-commit/partial-rollback machinery is needed because nothing ever gets far enough to need rolling back — the failed item is filtered out *before* note application runs, not caught as an exception *during* it.

**Consequence for cursor advancement (FR-012)**: since the note commits either way, `record_synced_notes`/`last_synced_mod` still advance for that deck's run as today. "Not advanced as if that item succeeded" is satisfied differently than a literal cursor-rollback would suggest: the failed hash simply never reaches `commit_media`'s returned map, so the *next* delta/full still lists it as missing (server-side `since_mod` filtering is by note `mod`, not by media hash — an unresolved `<img src>` stays unresolved until a later sync successfully stages that hash and rewrites it in a subsequent `apply_delta` pass over that same, already-synced note). This requires no new local bookkeeping: the note is simply reprocessed next time the deck's media manifest still lists that hash as `ready` but the local reference wasn't rewritten yet — `stage_media`'s collection-media existence check (§2 amendment, T010) naturally retries it.

**Alternatives considered**: Full per-deck rollback on any single media failure (today's literal behavior before this feature). Rejected: directly contradicts FR-012/Edge Cases' explicit wording and would make one broken image in a 50-note deck block every other note's sync indefinitely.

## 10. Media-download concurrency default (resolves `/speckit-analyze` finding F3)

**Decision**: Default concurrency limit of **4** simultaneous media downloads per sync/publish run, configurable via the same add-on config mechanism as `connection_settings` (`main/constants.py`).

**Rationale**: Low enough to stay well under typical OS per-host connection limits and Storage-provider fairness without any per-request coordination logic, high enough to meaningfully parallelize a "dozens of images" manifest (User Story 4's own scale reference) instead of serializing every download. Matches common defaults for this class of bounded-fan-out client work (e.g., `requests`-based batch downloaders commonly default in the 4-8 range) without requiring benchmarking infrastructure this increment doesn't otherwise need (YAGNI).

**Alternatives considered**: Unbounded (rejected — exactly what FR-019 exists to prevent); 1 (fully serial — rejected, defeats the purpose of adding concurrency for User Story 4's responsiveness goal); a number derived from `RATELIMIT_MEDIA_RATE` (rejected as over-engineering for this increment — the backend rate limit already governs total throughput independently of client-side concurrency, and coupling the two would require the add-on to parse/track a setting it doesn't otherwise need).
