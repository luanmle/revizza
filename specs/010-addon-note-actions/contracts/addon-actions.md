# Contract: Add-on UI Actions ↔ Backend

Defines the three add-on actions, their trigger, visibility rule, and backend interaction. All network runs off the Qt thread via the existing `QueryOp(...).without_collection().run_in_background()` pattern (FR-009).

## Visibility rule (all actions)

An action is offered for the current note **iff** its GUID is present in the local `SyncStateCache` (i.e. the note belongs to a subscribed Revizza deck). Otherwise the action is hidden/disabled (FR-001). Helper: `deck_id_for_guid(guid) -> str | None`.

## Action 1 — "Ver no Revizza" (reviewer bottom bar)

- **Trigger**: button injected into `mw.reviewer.bottom.web` on `reviewer_did_show_question` / `reviewer_did_show_answer`; click → `pycmd('revizza:view')` → `webview_did_receive_js_message`.
- **Behaviour**: `openLink(f"{API_BASE}/go/note/{guid}/")`. No blocking call, no auth required (FR-010).
- **Failure**: browser handles unreachable host; a `404` from the redirect lands on a "nota não encontrada" page — acceptable, no add-on crash.

## Action 2 — "Ver histórico" (reviewer bottom bar)

- **Trigger**: same injection; `pycmd('revizza:history')`.
- **Behaviour**: `openLink(f"{API_BASE}/go/note/{guid}/history/")` → suggestions view filtered to the note. Empty history shows the page's empty state, not an error (US3 #2).

## Action 3 — "Sugerir mudança" (note editor)

- **Trigger**: toolbar button added in `editor_did_init_buttons`; enabled/disabled per visibility rule on `editor_did_load_note`.
- **Pre-check (offline, FR-008)**: `hash(current_fields) == SyncStateCache.field_hash` → show "Nada a sugerir" and stop. Else open the suggestion dialog (category select + justification, mirroring the web form).
- **Submit**:
  1. `GET /notes/resolve/?guid=<guid>` → `note_id` (auth required; `401` → prompt login, keep draft).
  2. `POST /notes/{note_id}/suggestions/change/` with `{fields, tags, category, justification}`.
  3. `201` → confirmation toast in Anki; the suggestion appears on the web Community Suggestions (FR-007).
  4. `400` (`is_noop`) → "Nada a sugerir". Other non-2xx → plain-language error, draft preserved (FR-009).
- **Constraint**: single open note only; bulk stays web-only. This is a **proposal** into moderation — no direct content push (Principle II).

## Non-interference (Principle VIII)

None of the three actions read or write card scheduling (`cards`/`revlog`) or trigger a sync. The editor button reads the note's field values (Note Content) only.
