# Feature Specification: Hardened Add-on Media Sync

**Feature Branch**: `011-addon-media-sync`

**Created**: 2026-07-17

**Status**: Draft

**Input**: User description: "Implemente suporte robusto à sincronização de imagens entre o add-on Anki ankihub_br e a plataforma Revizza, corrigindo o fluxo de mídia já existente." (Deliver robust image sync between the ankihub_br Anki add-on and the Revizza platform, fixing the existing media flow — see known problems, mandatory functional scope, acceptance criteria, and out-of-scope list captured verbatim in the originating request.)

## Codebase Verification Summary

Findings from inspecting the current implementation before writing this spec (informs the requirements below, no code changed):

- `addon/ankihub_br/main/media.py::sync_media` writes downloaded bytes straight to `media_dir / item["filename"]` via `Path.write_bytes()`. The `filename` comes verbatim from the server payload — nothing strips path separators, so a malicious or malformed `filename` (e.g. `../../file`) can escape the media folder, and two decks that happen to publish a file with the same name silently overwrite each other locally.
- The installed Anki media API (`anki.media.MediaManager`, verified in the active `uv` environment at `anki/media.py:90-101`) exposes `col.media.add_file(path)` and `col.media.write_data(desired_fname, data)`. Both route through `col._backend.add_media_file(...)`, which sanitizes the filename, resolves it to the media folder only, and **renames on collision** (never overwrites) — this is the correct write primitive; the add-on currently bypasses it.
- `addon/ankihub_br/main/publish.py::build_publish_payload` already computes SHA-256 correctly, dedupes by hash within one publish payload, and only references media actually present in `col.media.files_in_str(...)` for the note's fields — this part does not need to change.
- `addon/ankihub_br/main/backup.py` snapshots the whole `.anki2` file (closed collection, file copy) before a sync run and restores it on failure. Media files under `collection.media/` are **not** part of that backup/restore, so a crash mid-download can leave a corrupt or partial file in the media folder that the restored collection then still points to.
- `addon/ankihub_br/ankihub_br_client/client.py::download_file` and `upload_signed_media` run synchronously on whatever thread calls them; `sync_decks`/`perform_sync` in `main/sync.py` call `media_mod.sync_media` inline, in the same flow as the rest of delta/full application. Existing background-op usage (`aqt.operations.QueryOp`) already exists elsewhere in the add-on (`gui/__init__.py`, `gui/editor.py`), establishing the pattern to reuse rather than invent a new one.
- Backend `PublishView` (`backend/apps/sync/views.py:257-364`) commits `Deck`/`NoteType`/`Note` in one atomic transaction, then creates `MediaFile` rows and issues signed upload URLs for new hashes — all inside the same transaction, but the actual byte upload to Storage happens **after** the response returns (in the add-on, via `publish_initial_deck`). A `MediaFile` row therefore exists, and the deck is publicly listed, before the corresponding object is guaranteed to be in Storage. `contracts/sync.md` already documents this as a deliberate best-effort tradeoff ("uma falha isolada de mídia não desfaz a publicação", clarified 2026-07-14) but does not define what a subscriber's sync sees in the window before upload completes.
- `MediaDownloadView` (`views.py:226-254`) returns a signed URL only when a `MediaFile` row exists **and** the requesting user is subscribed to its deck — it does not currently check whether the underlying Storage object exists, so a subscriber can receive a signed URL for an object that was never actually uploaded.
- `MediaFile` (`backend/apps/notes/models.py:53-68`) has no status/state field — it is implicitly "ready" the instant the row is created, which is exactly the gap called out above.
- `backend/tests/contract/test_sync_media.py` covers `GET /media/{hash}/` (subscription check, unknown hash, per-user rate limit) but there is no add-on-side test for the download-and-write path, and no test for the publish-time upload confirmation gap.

## Clarifications

No open `[NEEDS CLARIFICATION]` markers. One scope-defining question came up during verification — resolved with a documented default (see **Assumptions**) instead of blocking: whether media already published under the old (server-supplied, non-deterministic) filename scheme must be retroactively migrated. Default: no retroactive migration; only newly uploaded media adopt hash-derived filenames, so this feature has no data-migration step and does not touch existing `MediaFile` rows beyond adding the new status field with a backward-compatible default.

### Session 2026-07-17

- Q: Max per-file media size the add-on should enforce before rejecting a download (FR-009, SC-003)? → A: 10 MB.
- Q: After uploading media during publish, how should the add-on tell the backend an upload is confirmed (FR-006)? → A: Per-file confirm — one confirm call immediately after each successful `upload_signed_media`, not batched at the end.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A note with an image syncs correctly to a new Anki profile (Priority: P1)

A student subscribes to a deck whose notes include images (e.g., an anatomy diagram or an exam facsimile). When the add-on syncs, the note's HTML field already references an image; that image must actually exist and render inside Anki after sync, on any profile syncing the deck for the first time or picking up an image added since their last sync.

**Why this priority**: Without this, the entire feature is broken — images are the reason this spec exists. Every other requirement (integrity, resumability, responsiveness) exists to make this base case reliable at scale.

**Independent Test**: Publish a deck containing a note with an `<img>` reference, subscribe from a second (empty) profile, run sync, and confirm the image file is present in the collection's media folder and renders on the card.

**Acceptance Scenarios**:

1. **Given** a deck with a note containing one referenced image, **When** a subscriber runs their first (full) sync, **Then** the image file is written into the collection media folder under a name that matches what the note's HTML field references, and the card renders the image.
2. **Given** an already-synced deck, **When** a moderator-approved note edit adds a new image and the subscriber runs a delta sync, **Then** only the new image is downloaded and installed; unrelated, already-present media is left untouched.
3. **Given** a note references an image that is byte-for-byte already present locally under a different name (e.g., synced earlier via another deck), **When** sync runs, **Then** the add-on does not re-download it and correctly reuses or re-links the existing local copy.

---

### User Story 2 - Two decks with same-named, different-content media don't clobber each other (Priority: P1)

Two different decks each publish a file called `figura1.png` with different actual contents (e.g., two different moderators independently naming a screenshot the same generic name). A user subscribed to both must end up with both images intact and correctly associated with their respective notes.

**Why this priority**: This is a silent-data-corruption class of bug — a naive same-name write makes one deck's image quietly replace another's with no error raised anywhere, and is explicitly called out as a known problem.

**Independent Test**: Publish two decks each containing a note that references a same-named file with different byte content, subscribe to both from one profile, sync both, and verify each note shows its own distinct image.

**Acceptance Scenarios**:

1. **Given** two subscribed decks that each contain a file with the same original filename but different content hashes, **When** both are synced into the same profile, **Then** both files exist locally with distinct filenames and each note's field correctly references its own image.
2. **Given** the collision above already happened once, **When** either deck is synced again (delta or full), **Then** the previously resolved distinct filenames are reused — no renaming churn on every run.

---

### User Story 3 - Invalid or incomplete media is rejected without corrupting the collection (Priority: P1)

The add-on must never let a bad transfer — wrong hash, oversized file, truncated body, or an unsafe server-supplied name — reach the Anki media folder or the collection database.

**Why this priority**: Directly protects the constitution's "no direct schema changes"/collection-integrity guarantees and prevents both security issues (path traversal) and silent corruption (truncated image files that Anki can't render, or that later desync content vs. hash bookkeeping).

**Independent Test**: Simulate a download that returns a body whose SHA-256 doesn't match the manifest hash (or is oversized, or truncated by a dropped connection) and confirm the collection is unchanged and the file never lands under its final name.

**Acceptance Scenarios**:

1. **Given** a media manifest entry with a given `content_hash`, **When** the downloaded bytes hash to something else, **Then** the file is discarded, not written into the media folder, and the sync run reports this item as failed rather than succeeded.
2. **Given** a downloaded file exceeds 10 MB, **When** the add-on detects this (via `Content-Length` or streamed byte count), **Then** the transfer is aborted before the full body is buffered/written and the item is reported failed.
3. **Given** a server-supplied filename containing path separators or traversal sequences (`../`, absolute paths, drive letters), **When** the add-on processes the manifest entry, **Then** it never uses that value as a filesystem path — writes go through the collection's media API, which only ever resolves within the media folder.
4. **Given** the HTTP transfer is interrupted mid-stream, **When** the add-on detects the connection dropped, **Then** no partial file is left under the file's final name (a temp/staging location is used until validation passes) and retrying later can still complete.

---

### User Story 4 - Publishing and syncing large image sets keeps Anki responsive (Priority: P2)

A moderator publishes a deck with dozens of images, or a subscriber's delta pulls down many new images at once. Anki's UI must not freeze during this.

**Why this priority**: Lower than the correctness stories because a slow-but-eventually-correct sync is annoying; a frozen main thread that looks hung is a support-ticket generator and erodes trust, but it's a UX defect layered on top of an already-correct transfer, not a data-integrity one.

**Independent Test**: Publish/sync a deck with a large image set (or a single large image) and confirm the Anki window remains interactive (menus open, other windows respond) throughout, with visible progress.

**Acceptance Scenarios**:

1. **Given** a publish or sync operation involving multiple media files, **When** the operation is running, **Then** the main Anki window remains responsive (no UI freeze) and the user sees progress feedback.
2. **Given** a long-running media transfer, **When** the user closes the collection or the add-on needs to cancel, **Then** the operation stops cleanly without leaving the collection in a half-written state.

---

### User Story 5 - Interrupted sync can be safely retried (Priority: P2)

A sync is interrupted (app closed, network dropped, machine sleeps) partway through downloading several images. The next sync must pick up cleanly — not re-download what already succeeded, not skip what didn't, and not advance the sync cursor as if everything completed.

**Why this priority**: Directly required by the acceptance criteria and by the existing idempotent-delta contract (`contracts/sync.md`); without it, a flaky connection turns into permanently missing images that a normal resync never repairs.

**Independent Test**: Kill the add-on process (or mock a mid-batch exception) after some but not all media in a delta have downloaded successfully, then run sync again and confirm all media end up present with no duplicate downloads of the ones that already succeeded.

**Acceptance Scenarios**:

1. **Given** a sync run where some media downloads succeed and one fails, **When** the run ends, **Then** the local sync cursor (`last_synced_mod`) is only advanced for content that was fully and correctly applied, consistent with existing delta-application semantics.
2. **Given** a subsequent sync retries the same delta, **When** it runs, **Then** media already validated and written locally is not downloaded again, and only the previously failed/missing items are fetched.

---

### Edge Cases

- What happens when a note's HTML references an image whose hash was never included in the deck's media manifest (data inconsistency upstream)? The add-on must leave the field text untouched and skip only that reference, without failing the whole note/delta.
- What happens when the media manifest lists a `content_hash` the backend later reports as "not found" (404) — e.g., the row exists but Storage upload never completed? Treated as a transient/retryable failure (see User Story 3 and the backend-side "pending" state below), not a permanent one.
- What happens when the signed download URL has expired by the time the add-on gets to it (large batch, slow connection earlier in the run)? The add-on must be able to re-request a fresh signed URL and retry, not fail the whole sync.
- What happens when the same content hash is referenced by two different notes within the same deck? It is downloaded and validated once and reused for both — this already happens naturally once dedup-by-hash and the media API's own dedup-on-write are both in place.
- What happens when a deck publish is retried after a prior attempt partially uploaded some media (process crash between uploads)? Re-running publish for the same local deck must not create duplicate `MediaFile` rows and must resume uploading only the hashes not yet confirmed.
- What happens to orphaned temp/staging files left behind by a crash before this feature's cleanup logic ran (e.g., add-on updated mid-crash)? A stale-temp-file sweep runs at the start of the next media sync and removes anything older than one run's worth of time in the staging area.
- What happens when `429` is returned mid-batch by the per-user media-download rate limit already enforced by `MediaDownloadView`? The add-on respects `Retry-After`, pauses that batch, and resumes rather than treating it as a hard failure.

## Requirements *(mandatory)*

### Functional Requirements — Publish (add-on → backend)

- **FR-001**: The add-on MUST continue to identify media strictly by scanning the fields of notes actually being published (via the collection's media-reference extraction), never by scanning the whole media folder.
- **FR-002**: The add-on MUST compute a SHA-256 over each referenced file's bytes and MUST deduplicate by hash within a single publish payload (already satisfied by current `build_publish_payload`; preserved, not reintroduced).
- **FR-003**: The add-on MUST upload media directly to Storage using the signed URL returned by the backend, and MUST NOT send the API bearer token on that upload request.
- **FR-004**: A deck publish MUST remain resumable: re-running `publish_initial_deck` for a deck that already exists on the backend (409 case) or that partially uploaded media on a prior attempt MUST NOT create duplicate `MediaFile` rows and MUST only request/upload the hashes not yet confirmed as uploaded.
- **FR-005**: The backend MUST NOT treat a `MediaFile` as available for download until the corresponding upload has been confirmed; media referenced by `deck.media_files.all()` in delta/full/publish-echo payloads MUST be filtered to confirmed-only (or otherwise flagged) so a subscriber never receives a manifest entry pointing at an object that isn't actually in Storage yet.
- **FR-006**: The add-on MUST report an explicit "media upload confirmed" signal to the backend immediately after each individual successful `upload_signed_media` call (one lightweight confirm request per file, not batched at the end of publish), so the backend can flip the corresponding `MediaFile` to the ready state described in FR-005 as soon as it is true, and so a crash mid-publish leaves only the not-yet-confirmed files needing retry on the next attempt (FR-004).
- **FR-007**: A media upload failure during publish MUST NOT undo the already-committed note/note-type transaction (preserves the existing documented tradeoff in `contracts/sync.md`), but the affected `MediaFile` MUST remain in the not-ready state so it is retried on the next publish attempt or explicitly reported to the moderator as incomplete.

### Functional Requirements — Sync (backend → add-on)

- **FR-008**: The add-on MUST receive a media manifest (list of `{filename, content_hash}`, already part of the delta/full payload) and MUST download only entries that are missing locally or whose local content hash differs from the manifest.
- **FR-009**: Before writing any downloaded bytes into the collection, the add-on MUST validate: (a) the byte length does not exceed 10 MB, (b) the SHA-256 of the downloaded bytes matches the manifest's `content_hash` exactly, and (c) the response was fully received (no `Content-Length` mismatch / stream cut short).
- **FR-010**: Writing validated media into the collection MUST go exclusively through the collection's own media API (`col.media.write_data`/`add_file`) — the add-on MUST NOT construct filesystem paths from server-supplied filenames or write directly into the media directory.
- **FR-011**: To eliminate same-name/different-content collisions across decks (User Story 2) without relying on ad hoc rename bookkeeping, the add-on MUST derive the local media filename deterministically from the content hash and the original extension (e.g., `<sha256>.<ext>`) at write time, and MUST rewrite the corresponding `<img src="...">` reference(s) in the note's field value(s) to the resolved local filename before that note is committed to the collection.
- **FR-012**: A failed or skipped media item (validation failure, exhausted retries, 404/expired URL not recovered) MUST cause that item — and only the notes whose rendering depends on it — to be flagged as incomplete; the sync run's cursor/state MUST NOT be advanced as if that item succeeded (aligns with existing `record_synced_notes`/backup-restore semantics in `main/sync.py`).
- **FR-013**: A subsequent sync (retry, or the next scheduled delta) MUST be able to complete the previously failed items without re-downloading or re-validating media that already succeeded.
- **FR-014**: The add-on MUST use a temporary/staging write location for in-flight downloads and MUST only hand bytes to the collection media API after full validation passes; no partially-downloaded content may ever be reachable under a file's final resolved name.
- **FR-015**: The add-on MUST clean up temporary/staging files after each run, including a sweep for stale leftovers from a previous crashed run at the start of the next media sync.
- **FR-016**: Re-running the same delta (idempotency, FR-039-equivalent for media) MUST NOT duplicate, re-download, or corrupt already-valid local media.

### Functional Requirements — Responsiveness & Failure Handling

- **FR-017**: All network I/O and hashing/validation for media MUST run off the Qt main thread, using the add-on's existing background-operation pattern (`aqt.operations` `QueryOp`/`CollectionOp`, per the versions already in use elsewhere in the add-on) rather than blocking the UI thread.
- **FR-018**: Media downloads MUST enforce a request timeout and MUST retry only transient failures (network errors, `429`, `5xx`), honoring `Retry-After` when present — mirroring the retry policy already implemented for API calls in `AnkiHubBrClient`.
- **FR-019**: Media downloads MUST enforce a configurable concurrency limit so a large manifest does not open unbounded simultaneous connections.
- **FR-020**: The add-on MUST surface visible progress (count or percentage) during a media-heavy sync/publish operation.
- **FR-021**: The user MUST be able to cancel an in-progress media sync/publish without leaving the collection in a half-written state (any in-flight temp writes are discarded, already-committed items are kept).

### Functional Requirements — Backend API & Security

- **FR-022**: The existing `GET /api/v1/media/{content_hash}/` endpoint's authorization (subscriber-only, 403 for unauthorized existing hash, 404 for unknown hash) MUST be preserved unchanged for this increment.
- **FR-023**: `MediaDownloadView` MUST NOT return a signed URL for a `MediaFile` that is not yet confirmed uploaded (ties to FR-005/FR-006); it MUST respond in a way the add-on can treat as "not ready yet, retry" rather than a hard failure.
- **FR-024**: The backend MUST NOT introduce a batch multi-hash resolution endpoint in this increment — the current one-hash-per-request shape is retained because the manifest already carries hash+filename per item and the marginal round-trip savings do not justify a new contract surface yet (revisit only if telemetry shows median media-per-sync makes per-item requests a real bottleneck).
- **FR-025**: Existing rate limits (`RATELIMIT_MEDIA_RATE`, `RATELIMIT_PUBLISH_RATE`, per-user 10s sync-run guard) MUST remain in effect and MUST NOT be weakened to accommodate larger media batches — the add-on's concurrency/retry behavior (FR-018, FR-019) is what must adapt, not the server-side limits.
- **FR-026**: Signed upload/download URLs MUST continue to be Storage-native, pre-signed, and time-limited; the API layer MUST NOT proxy media bytes itself.

## Key Entities

- **MediaFile** (existing, `backend/apps/notes/models.py`): extended with a readiness state (e.g., `status`: `pending_upload` / `ready`) distinguishing "row created, upload URL issued" from "upload confirmed" — see FR-005/FR-006/FR-023. `content_hash`, `storage_path`, `original_filename`, and the per-deck hash uniqueness constraint are unchanged.
- **Media manifest item** (wire payload, existing `{filename, content_hash}` shape in delta/full/publish responses): unchanged shape; semantics tightened so only `ready` `MediaFile`s are ever included.
- **Local staging file** (new, add-on-local only, not persisted across runs beyond cleanup bookkeeping): an in-flight download destination distinct from the collection's media folder, used until FR-009's validation passes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A note with an image, published from one Anki profile, renders correctly (image visible, no broken-image icon) after a first-time full sync on a second profile, in 100% of manual test-matrix runs.
- **SC-002**: Two decks publishing same-named, different-content images never overwrite each other's file locally, verified across 100% of the automated collision test cases and the manual matrix.
- **SC-003**: Zero collection or media-folder corruption is observed across the automated fault-injection suite (bad hash, oversized body, truncated stream, path-traversal filename, mid-transfer interruption) — every case ends with an unchanged collection and no stray final-named partial file.
- **SC-004**: Re-running an already-successful sync or publish performs zero redundant media downloads/uploads, measured by request count in the automated suite.
- **SC-005**: Anki's main window stays responsive (accepts input, other dialogs open) throughout a test sync/publish involving a multi-file media batch, verified in the manual matrix on a real profile.
- **SC-006**: An interrupted sync followed by a retry reaches full completion (all media present and valid) without manual intervention, in 100% of the interruption-simulation test cases.
- **SC-007**: No note's field values, tags, or card scheduling data change as a side effect of this feature beyond the documented `<img src>` filename rewrite from FR-011, verified by diffing sync output against pre-feature behavior in the automated suite.

## Assumptions

- Existing, already-published `MediaFile` rows and any note HTML already referencing the old (server-original) filename scheme are left as-is; this feature does not retroactively rename or migrate previously synced media. Only files uploaded after this feature ships adopt hash-derived filenames (see **Clarifications**).
- "Images" in scope means the file types Anki already recognizes via `col.media.files_in_str` field scanning (standard raster/vector image formats referenced by `<img src>`); no new format allowlist is introduced by this feature. Audio/video already flowing through the same code path are not deliberately blocked, but no new support work is done for them.
- Maximum per-file size is fixed at 10 MB (see Clarifications, 2026-07-17); the default concurrency limit remains an add-on-side configuration value, and its exact number is a planning-phase decision, not a product requirement.
- The add-on continues to run all media handling through the existing single-run backup (`main/backup.py`) — this feature does not change the collection-file backup mechanism itself, only ensures the media write path can never leave the *media folder* corrupted regardless of whether the `.anki2` backup covers it.
- "Batch resolution endpoint" evaluation (FR-024) is a one-time judgment call for this increment based on current manifest shape; it is not a permanent architectural decision and may be revisited if usage data changes the calculus.

## Test Plan Notes

- **Automated (backend, pytest)**: extend `backend/tests/contract/test_sync_media.py` with cases for the new `pending_upload`/`ready` status gate on `MediaDownloadView`, and add a contract test for the new upload-confirmation call from FR-006.
- **Automated (add-on, pytest, mocked collection + mocked `AnkiHubBrClient`)**: hash-mismatch rejection, oversized-body rejection, truncated-stream rejection, path-traversal filename rejection, same-name/different-hash collision across two decks, idempotent re-sync (no re-download), interrupted-then-resumed delta, stale-staging-file sweep.
- **Manual test matrix (real Anki profile, per release)**: first full sync of an image-heavy deck; delta sync adding one new image to an existing deck; two decks with colliding filenames subscribed together; forced network drop mid-sync followed by retry; large single-image (multi-MB) publish and sync while interacting with other Anki windows; publish retried after simulated crash between two media uploads.
