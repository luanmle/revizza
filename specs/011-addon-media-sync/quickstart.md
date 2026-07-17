# Quickstart: Validating Hardened Add-on Media Sync

Prerequisites: backend running locally with the new `MediaFile.status` migration applied; a Supabase Storage bucket reachable (or the media-signing functions monkeypatched, as the existing contract tests already do); an add-on dev checkout with a real or headless Anki collection.

## 1. Automated backend contract checks

```bash
cd backend
uv run pytest tests/contract/test_sync_media.py -v
```

Expected: existing subscription/404/rate-limit cases still pass; new cases pass for:
- `status=pending_upload` hash returns 404 from `GET /media/{hash}/` even for a subscribed user (contracts/media-sync.md §2).
- `POST /decks/{id}/media/{hash}/confirm/` flips status and is idempotent on repeat calls (contracts/media-sync.md §4).
- delta/full responses never list a `pending_upload` hash in `media` (contracts/media-sync.md §1).

## 2. Automated add-on checks

```bash
cd addon
uv run pytest tests/unit/test_media_sync.py tests/unit/test_media_publish.py -v
```

Expected coverage per spec's Test Plan Notes: hash-mismatch rejection, oversized-body rejection (>10 MB), truncated-stream rejection, path-traversal filename never reaches the filesystem, two-deck same-name/different-hash collision resolves to two distinct local files, idempotent re-sync does not re-download validated media, an interrupted-then-resumed delta completes without duplicating work, a stale staging file from a simulated crash is swept on the next run, and the Principle VIII scheduling-immutability assertion (contracts/media-sync.md, final section) passes.

## 3. End-to-end manual scenario (User Story 1 — happy path)

1. In a local/dev backend, create a deck via the add-on's "Criar deck Revizza" flow from a profile with one note containing an `<img>`-referenced image.
2. Confirm in Django admin (or a quick shell query) that the resulting `MediaFile` row starts `pending_upload` and flips to `ready` shortly after publish completes (the add-on's per-file confirm call).
3. From a **second, empty** Anki profile, log in and subscribe to that deck; trigger a manual sync.
4. Open the synced note in the Anki browser/reviewer and confirm the image renders (no broken-image icon), and that `collection.media/` contains a file named `<sha256>.<ext>` — not the original filename.

Expected outcome matches spec Success Criteria SC-001.

## 4. Manual collision scenario (User Story 2)

1. Publish deck A with a note referencing a file literally named `figura1.png` (content X).
2. Publish deck B (different deck) with a note referencing a different file, also named `figura1.png` (content Y ≠ X).
3. From one profile, subscribe to both A and B and sync.
4. Confirm both notes render their own correct, distinct image — verify two different files exist locally (named by their respective content hashes) and neither note's `<img src>` points at the other's content.

Expected outcome matches SC-002.

## 5. Manual interruption scenario (User Story 5)

1. Publish a deck with several (5+) images.
2. Subscribe from a fresh profile; start a sync; kill the Anki process partway through the media batch (or use a debugger breakpoint / temporary `raise` injected mid-loop in a dev build).
3. Restart Anki, open the same profile, sync again.
4. Confirm all images end up present and valid, and (via added logging or a breakpoint) that images already validated on the first attempt were not re-downloaded on the second.

Expected outcome matches SC-006.

## 6. Manual responsiveness scenario (User Story 4)

1. Publish/sync a deck with a large image set (10+ files, at least one near the 10 MB cap) on a throttled/slow connection (OS-level network throttle or a local proxy that delays responses).
2. While the sync/publish runs, interact with Anki: open the deck list, open another dialog, move the main window.
3. Confirm the UI never freezes/beachballs and a progress indication is visible.

Expected outcome matches SC-005.

## Full test-plan cross-reference

See spec.md's **Test Plan Notes** section for the complete automated-test and manual-matrix list this quickstart samples from; `/speckit-tasks` is responsible for turning that full list into concrete task entries, including the Principle VIII scheduling-immutability test flagged in `contracts/media-sync.md`.
