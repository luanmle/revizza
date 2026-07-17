# Contract: Hardened Add-on Media Sync (011)

Extends `specs/001-ankihub-brasil-mvp/contracts/sync.md`. Only the deltas from that base contract are documented here; everything not mentioned (auth model, rate-limit headers, versioning via `Accept`) is unchanged.

## 1. `GET /api/v1/decks/{id}/sync/delta/` and `GET /api/v1/decks/{id}/sync/full/`

**Change**: the `media` array in the response now only ever contains `MediaFile` rows with `status = "ready"`. Wire shape of each item is unchanged: `{"filename": str, "content_hash": str}`.

No new query parameters, no new response fields. A subscriber whose delta window includes a note referencing a still-`pending_upload` file simply doesn't see that hash in `media` yet — it appears on a later delta once the moderator's upload is confirmed. The note's field HTML is unaffected either way (still contains the eventual hash-derived `<img src>` once the add-on resolves and rewrites it locally on the sync that first includes that hash).

## 2. `GET /api/v1/media/{content_hash}/`

**Change**: gate on `status`, not just existence + subscription.

| Condition | Response |
|---|---|
| No `MediaFile` with this hash exists at all | `404 {"detail": "Mídia não encontrada."}` (unchanged) |
| `MediaFile` exists, requester not subscribed to its deck | `403 {"detail": "Assine o deck para baixar esta mídia."}` (unchanged) |
| `MediaFile` exists, requester subscribed, `status = "pending_upload"` | **new**: `404 {"detail": "Mídia ainda não disponível."}` — same status code as "unknown hash" so the add-on's retry logic doesn't need to distinguish "will never exist" from "not ready yet"; the manifest already won't list a `pending_upload` hash (§1), so this case is reached only via a stale client-side hash reference, not the normal happy path |
| `MediaFile` exists, requester subscribed, `status = "ready"` | `200 {"url": "<signed>", "filename": "<original_filename>"}` (unchanged) |

Rate limiting (`RATELIMIT_MEDIA_RATE`, per-user, `429` with `Retry-After: 60`) unchanged.

## 3. `POST /api/v1/decks/{id}/publish/`

**Unchanged** request/response shape: still create-only, still 409 if the deck exists, still returns `media_upload_urls: {content_hash: signed_url}` for every newly created (now: newly `pending_upload`) `MediaFile`. No behavior change to the atomic note/note-type transaction.

## 4. `POST /api/v1/decks/{id}/media/{content_hash}/confirm/` — **new**

Confirms that a previously-issued signed upload URL for this deck+hash was used successfully. Flips the matching `MediaFile.status` from `pending_upload` to `ready`.

**Auth**: same authorization as `PublishView` — the deck's creator, or a moderator in `DeckModerator` (matches "only the party that could have received the upload URL can confirm it").

**Request**: `POST`, empty body.

**Responses**:

| Condition | Response |
|---|---|
| No `MediaFile` for this `(deck_id, content_hash)` | `404 {"detail": "Mídia não encontrada para este deck."}` |
| Caller not creator/moderator of the deck | `403 {"detail": "Apenas o criador ou moderadores do deck podem confirmar uploads."}` |
| `MediaFile` found, `status` already `ready` | `200 {"content_hash": "...", "status": "ready"}` — idempotent no-op, not an error (FR-004 resumability) |
| `MediaFile` found, `status = pending_upload` | flips to `ready`, `200 {"content_hash": "...", "status": "ready"}` |

**Rate limiting**: reuse `RATELIMIT_PUBLISH_RATE` semantics (same actor, same operation family as publish) — not a new rate-limit setting.

**Explicitly not implemented**: no verification that the object actually exists in Storage (no HEAD request to Supabase Storage from this endpoint). The add-on only calls confirm after its own `upload_signed_media` PUT already succeeded (2xx) — trusting the add-on's own successful upload response is consistent with how `PublishView` already trusts the add-on's reported `content_hash`/field values today, and adding a server-side Storage existence check is out of scope for this increment (would require a new Storage API round-trip for marginal benefit — no known failure mode this would catch that the add-on's own upload success/failure doesn't already catch).

## 5. Add-on client surface (`AnkiHubBrClient`) — new/changed methods

Not a network contract in the REST sense, but the internal boundary this feature adds to/changes:

- **New**: `confirm_media_upload(deck_id: str, content_hash: str) -> None` — calls §4.
- **Changed**: `download_file(url: str) -> bytes` becomes streamed with a 10 MB cap (research.md §5) and routes through `self.session` instead of a bare `requests.get` (research.md §6) — same signature, same return type, callers unaffected.

## Constitution Principle VIII test obligation

Any automated test exercising `apply_delta`/`apply_full` with a media-bearing payload (i.e. covering FR-011's filename rewrite) MUST assert that a card's scheduling fields (whatever the test collection's `find_cards`/`get_card` exposes for `due`, `ivl`, `factor`, `reps`, `queue`) are byte-identical before and after the sync, per the constitution's Principle VIII planning-governance requirement. This is a required test-plan item for `/speckit-tasks`, not optional coverage.
