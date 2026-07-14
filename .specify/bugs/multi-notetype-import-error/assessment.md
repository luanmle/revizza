# Bug Assessment: "A importação inicial aceita um único tipo de nota por deck"

- **Slug**: multi-notetype-import-error
- **Created**: 2026-07-14
- **Source**: pasted text
- **Verdict**: invalid (expected behavior, not a bug) — with a UX gap worth fixing
- **Severity**: low

## Report (verbatim or summarized)

> ao tentar fazer upload de um deck add-on retornou o erro: "A importação falhou: A importação inicial aceita um único tipo de nota por deck."

## Symptom

User tried to publish/upload a local Anki deck via the add-on and got a hard failure. Expected: upload succeeds (or a clear pre-flight warning, not a failed API round-trip).

## Reproduction

1. In Anki, select a deck that contains notes of **more than one note type**.
2. Use the Revizza add-on's "Publicar deck" flow to import it.
3. Add-on raises `PublishError("A importação inicial aceita um único tipo de nota por deck.")`, caught by the generic `except Exception` handler in the GUI, shown as `showWarning(f"A importação falhou: {exc}")`.

## Suspected Code Paths

- `addon/ankihub_br/main/publish.py:35-40` — `build_publish_payload` collects all `note.mid` across the deck's notes; if `len(notetype_ids) != 1`, raises `PublishError`. This is the source of the message.
- `addon/ankihub_br/gui/__init__.py:329-348` — calls `publish.publish_initial_deck`, catches `Exception`, surfaces the message directly with no pre-check before the call and no deck-composition hint in the error itself.

## Root Cause Hypothesis

Not a defect. `specs/001-ankihub-brasil-mvp/data-model.md:38` explicitly documents the constraint: "um deck usa um tipo de nota (pode ser estendido a N no pós-MVP)" — one note type per deck is deliberate MVP scope, deferred to post-MVP. The add-on is correctly rejecting an unsupported deck shape (a deck mixing note types, e.g. Basic + Cloze). Confidence: high.

The rough edge is UX: the user only discovers the single-notetype constraint after attempting a full upload, and the message doesn't say *which* note types were found or how many notes are affected, making it hard to know which notes to move/split.

## Proposed Remediation

**Preferred**: Not a code fix — no change needed to the create-only-single-notetype rule itself (constitution/PRD-aligned). If the user wants better UX, two independent, purely additive improvements (out of scope unless requested):
- Improve the error string in `publish.py:37-40` to name the offending note types (e.g. list `notetype.get("name")` for each id) so the user knows what to reorganize, e.g. `f"A importação inicial aceita um único tipo de nota por deck. Encontrados: {', '.join(sorted(names))}."`
- Optionally add a pre-flight check in the GUI publish dialog (before hitting the network) that inspects note types up front and disables/warns, instead of relying on the exception path — this is a UX nicety, not correctness.

**Alternatives** (optional):
- None — expanding to multi-notetype decks is explicitly deferred to post-MVP per the data model; do not implement that now.

**Files likely to change** (only if user requests the UX tweak):
- `addon/ankihub_br/main/publish.py`
- `addon/ankihub_br/tests/test_publish.py` (or equivalent) — assert the improved message lists notetype names

**Tests to add or update**:
- If message is enriched: a unit test asserting `PublishError` message includes both notetype names when a deck has 2 note types.

## Risks & Considerations

- None for the "no fix" path (current behavior is correct per spec).
- If message is enriched, no behavior change, purely cosmetic — no migration/API risk.

## Open Questions

- [NEEDS CLARIFICATION: does the user want the error message improved (list offending note types) or a pre-flight check added, or is this assessment sufficient to close as "working as intended"?]
