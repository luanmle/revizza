# Implementation Plan: Hardened Add-on Media Sync

**Branch**: `011-addon-media-sync` | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-addon-media-sync/spec.md`

## Summary

Fix the add-on's media pipeline so images referenced in note fields publish, download, and install correctly without corrupting the collection, colliding across decks, or freezing the Anki UI. The unsafe write (`Path.write_bytes()` on a server-supplied filename) is replaced by staging + validating downloads off the main thread, then committing them through Anki's own `col.media.write_data` (which sanitizes names and never overwrites), with local filenames derived deterministically from the content hash so two decks can never clobber each other. On the backend, `MediaFile` gains a `pending_upload`/`ready` status so a subscriber can never receive a signed URL for an object that isn't actually confirmed in Storage yet, closing the gap between "publish transaction committed" and "media upload actually finished."

## Technical Context

**Language/Version**: Python 3.12 (both `backend/` and `addon/`); add-on runs embedded in Anki Desktop ≥26.0 (per `addon/requirements.txt` and `compat.SUPPORTED_LTS_PREFIX`).

**Primary Dependencies**: Add-on: `anki`/`aqt` (`anki.media.MediaManager`, `aqt.operations.QueryOp`), `requests` (existing retry/backoff session in `AnkiHubBrClient`), `peewee` (local `SyncStateCache`, unaffected by this feature). Backend: Django + DRF, `django-ratelimit`, `supabase-py` (`apps/sync/media.py` signed URLs).

**Storage**: Postgres via Supabase (`MediaFile` row gains a status field — new migration in `apps/notes`); Supabase Storage for media bytes (unchanged, pre-signed URLs only); local Anki SQLite media folder, written exclusively through `col.media` from now on; add-on's own local SQLite state cache (`db/models.py`) is untouched by this feature.

**Testing**: pytest on both sides — `backend/tests/contract/test_sync_media.py` (extended) and `backend/tests/unit/`; `addon/tests/unit/` with a headless `anki.collection.Collection` (no `pytest-anki`, per existing `ponytail:` note in `requirements.txt` — Qt6 incompatibility) and a mocked `AnkiHubBrClient`.

**Target Platform**: Anki Desktop add-on (Windows/macOS/Linux, one supported LTS at a time) talking HTTPS to a Django API on Heroku.

**Project Type**: Web application (Django backend + Next.js frontend, per repo convention) plus a third, independently-packaged component: the Anki desktop add-on. This feature only touches `backend/` and `addon/` — no frontend change.

**Performance Goals**: No new formal throughput target; existing per-user 10s sync-run guard and `RATELIMIT_MEDIA_RATE`/`RATELIMIT_PUBLISH_RATE` are preserved unchanged (FR-025). Qualitative goal only: Anki's main window must stay responsive during a multi-file media sync/publish (SC-005).

**Constraints**: Max 10 MB per media file (clarified 2026-07-17); configurable download concurrency limit, default 4 (research.md §10); all media network I/O off the Qt main thread (FR-017); no partial file ever reachable under its final resolved name (FR-014); zero change to note field/tag/scheduling data beyond the documented `<img src>` filename rewrite (SC-007); no bearer token on Storage upload/download requests (existing constraint, preserved).

**Scale/Scope**: One feature increment — hardens the existing single-deck-at-a-time media pipeline (`sync_decks` already loops decks sequentially within one backup/run). No change to how many decks or images a deck may contain; "dozens of images" is the manual-test-matrix scale (User Story 4), not a new hard limit.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies? | Assessment |
|---|---|---|
| I. Parity Over Reinvention | Yes | Media handling mirrors AnkiHub's own model: hash-addressed content, deduped by hash, fetched via signed URL, written through the native media API. No novel protocol invented. Deterministic hash-derived local filenames (FR-011) is a deliberate, spec-justified deviation from "keep server filename as-is" — justified because it is the only way to guarantee cross-deck collision-freedom without ad hoc rename bookkeeping (spec Edge Cases / User Story 2), and AnkiHub's own add-on similarly does not trust server filenames as final local names. |
| II. Unidirectional Sync (NON-NEGOTIABLE) | Yes | No change to direction of content flow: publish is still create-only upload, sync is still pull-only apply. Media confirm calls (FR-006) are metadata-only acknowledgements of an upload already permitted by Principle II's one-time create-only import, not a new upstream content channel. |
| III. Privacy & LGPD | No | Feature touches no personal data categories, consent flags, or export/deletion flows. |
| IV. Secure by Default | Yes | Directly implements: HTTPS-only transport (already enforced by `AnkiHubBrClient`), no plaintext write of untrusted server filenames to disk (FR-010), size/hash/completeness validation before any collection mutation (FR-009), existing rate limits preserved not weakened (FR-025), no bearer token leaked to signed Storage URLs (FR-003, pre-existing and preserved). |
| V. MVP Scope Discipline (YAGNI) | Yes | FR-024 explicitly declines to add a batch media-resolution endpoint this increment, reasoning it out rather than building it "just in case." No thumbnailing/transcoding/audio-video work added (spec Out of Scope). |
| VI. Current Docs & Minimal Code | Yes | `col.media.add_file`/`write_data` signatures verified against the installed `anki` package source (not memorized) before this plan/spec were written (see spec's Codebase Verification Summary). Design reuses the existing `QueryOp(...).without_collection()` pattern already established in `gui/__init__.py`/`gui/editor.py` rather than introducing a new concurrency primitive. |
| VII. Design Tooling Pipeline | No | No UI/screen work — add-on has no web-style screens; any Qt progress-dialog text is a one-line label, not a new screen. |
| VIII. Sync Fidelity & State Separation (NON-NEGOTIABLE) | Yes | This plan touches sync endpoints and the `Note`-adjacent `MediaFile` model, so it must address this explicitly: media is pure Note Content (an image referenced by a field's HTML) and never touches `cards`/`revlog` scheduling tables. The FR-011 filename rewrite modifies only the note's field HTML string (`<img src>` attribute), the same class of mutation `_apply_notes`/`_fill_fields` already performs for other field content — it does not touch `col.sched`, due dates, ease, or review history. Task list (Phase 2) MUST include an automated test asserting a media-bearing delta/full application leaves a card's scheduling fields (due, ivl, factor, reps — whatever the test collection already has) byte-identical before/after. |

**Gate result**: PASS. One documented, justified deviation (hash-derived local filenames vs. verbatim server filename) under Principle I; no unjustified violations. Complexity Tracking table not required.

## Project Structure

### Documentation (this feature)

```text
specs/011-addon-media-sync/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
│   └── media-sync.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── notes/
│   │   ├── models.py                 # MediaFile: add `status` field (migration)
│   │   └── migrations/000X_media_file_status.py
│   └── sync/
│       ├── views.py                  # MediaDownloadView: gate on status=ready
│       │                             # PublishView: return per-hash upload URLs only (no behavior change to atomicity)
│       │                             # new: MediaUploadConfirmView (POST /decks/{id}/media/{hash}/confirm/)
│       ├── media.py                  # unchanged (signed URL helpers)
│       └── urls.py                   # register confirm route
└── tests/
    └── contract/test_sync_media.py   # extend: status gating, confirm endpoint

addon/
├── ankihub_br/
│   ├── main/
│   │   ├── media.py                  # split: stage_media() [network+validate, no col] / commit_media() [col write only]
│   │   ├── publish.py                # publish_initial_deck: call confirm endpoint per uploaded file
│   │   ├── sync.py                   # perform_sync: stage media before apply_delta/apply_full, pass filename map in
│   │   └── backup.py                 # unchanged (media staging never touches final media dir until validated)
│   ├── ankihub_br_client/client.py   # download_file: stream + size cap; add confirm_media_upload()
│   └── gui/__init__.py               # sync_all: wrap network+staging phase in QueryOp(...).without_collection()
└── tests/
    └── unit/
        ├── test_media_sync.py        # new: hash/size/traversal rejection, collision, idempotent retry
        └── test_media_publish.py     # new: resumable publish, per-file confirm
```

**Structure Decision**: Follows the existing repo layout exactly (`backend/apps/*`, `addon/ankihub_br/*`) — no new top-level directories. The only structural addition is one new backend view/route (media upload confirmation) and a split of `addon/ankihub_br/main/media.py` into a network/staging half and a collection-write half, mirroring the constitution's existing "minimal code, reuse established patterns" mandate rather than introducing a new module or service boundary.

## Complexity Tracking

*No unjustified Constitution Check violations — table intentionally empty.*
