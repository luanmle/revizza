# Quickstart: Validate catalog discovery

## Prerequisites

- Backend and frontend local environment configured.
- At least one user with an active subscription, one user who actively moderates a deck, one official
  deck, one non-official deck, and decks with different note counts/subscriber counts/content update
  times.
- Migrations applied after adding `Deck.creator` and `Deck.is_official`.

## Backend contract checks

Run from `backend/` after implementation:

```bash
pytest tests/contract/test_catalog_tabs.py tests/contract/test_catalog_trust_fields.py tests/contract/test_catalog_sorting.py -q
```

Expected coverage:

- `GET /api/v1/decks/?moderated=1` returns exactly actively moderated decks for the user.
- `GET /api/v1/decks/?subscribed=1` still returns the subscribed set used by the add-on.
- `tag`, personal filter, and `sort` combine correctly.
- All five sort values produce expected stable order.
- Cursor pagination does not skip or repeat results for unchanged query state.
- List/detail responses include `creator`, `last_updated_at`, and `is_official`.
- Detail response includes active moderator avatar summaries.
- Moderator deck edit flows cannot set `is_official`.

## Frontend checks

Run from `frontend/` after implementation:

```bash
npm run test
npm run test:e2e -- --project=chromium
```

Manual smoke path:

1. Open `/decks`.
2. Switch tabs: "Catálogo", "Meus baralhos", "Inscritos".
3. Apply a tag filter, then switch sort to each option.
4. Confirm URL keeps tab/tag/sort and pagination resets after each change.
5. Confirm cards show creator avatar/name, "atualizado há ...", official badge only for official decks,
   note count, subscriber count, and tags.
6. Open a deck detail page and confirm creator and active moderator avatars appear.
7. Test at 360px and desktop width with Playwright screenshots; no horizontal scroll.

## Design quality gate

- Use existing `frontend/design-system/MASTER.md` rules: restrained product UI, emerald primary,
  shadcn primitives, visible labels/focus, skeleton loading, clear empty states.
- Run visual inspection/audit after screenshots: tab/select/card layout must remain readable at 360px;
  no nested cards, no decorative gradients, no text overflow.

## Expected outcome

All scenarios pass, matching SC-001 through SC-006 in [spec.md](./spec.md).
