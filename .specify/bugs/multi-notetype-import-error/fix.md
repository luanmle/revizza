# Bug Fix: "A importação inicial aceita um único tipo de nota por deck"

- **Slug**: multi-notetype-import-error
- **Fixed**: 2026-07-14
- **Assessment**: ./assessment.md
- **Status**: applied

## Summary

Not a bug (single-notetype-per-deck is deliberate MVP scope). Per user confirmation, applied the assessment's optional UX improvement: the error message now names the offending note types instead of just stating the constraint.

## Changes

| File | Change | Notes |
|------|--------|-------|
| `addon/ankihub_br/main/publish.py` | modified | `build_publish_payload` now resolves `notetype_ids` to names via `col.models.get(mid)["name"]` and appends `"Encontrados: <names>."` to the `PublishError` message |
| `addon/tests/unit/test_publish.py` | modified | `test_rejects_deck_with_multiple_note_types` now asserts both notetype names ("Alternativo" and the deck's default current model name) appear in the raised message |

## Diff Highlights

```python
notetype_ids = {note.mid for note in notes}
if len(notetype_ids) != 1:
    names = sorted(
        {col.models.get(mid)["name"] for mid in notetype_ids}
    )
    raise PublishError(
        "A importação inicial aceita um único tipo de nota por deck. "
        f"Encontrados: {', '.join(names)}."
    )
```

## Tests Added or Updated

- `addon/tests/unit/test_publish.py::test_rejects_deck_with_multiple_note_types` — now pins down that both note type names appear in the exception message, not just the generic constraint text.

## Local Verification

- Commands run: `python3 -m pytest tests/unit/test_publish.py -q` → `3 passed in 0.54s`

## Deviations from Assessment

None. Assessment's preferred remediation (name the offending note types in the message) applied as proposed; pre-flight GUI check was listed as optional and not requested by the user, so skipped.

## Follow-ups

- None required. The single-notetype-per-deck constraint itself is out of scope for this fix — deliberate MVP limitation per `specs/001-ankihub-brasil-mvp/data-model.md:38`, deferred to post-MVP.
