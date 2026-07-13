# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

Implementation is underway (US1/US2 of the MVP spec are built; US3 partially). The repo holds:

- `PRD-AnkiHub-Brasil.md` — the product requirements document (in Portuguese) and the single source of truth for scope, user stories, and technical decisions.
- `specs/001-ankihub-brasil-mvp/` — the active spec-kit feature (spec, plan, tasks, contracts, data model).
- `.specify/` — a [spec-kit](https://github.com/github/spec-kit) (speckit) scaffold for spec-driven development (specify → plan → tasks → implement).
- `.specify/memory/constitution.md` — **ratified** (v1.2.0): seven principles including create-only initial deck import followed by unidirectional sync, LGPD by design, YAGNI, context7+ponytail code discipline, and the ui-ux-pro-max→impeccable design pipeline. Check it before starting any work.
- `backend/` (Django + DRF, pytest), `frontend/` (Next.js 16 + Tailwind 4 + shadcn/ui, Vitest/Playwright), `addon/` (Anki add-on, pytest) — see each subtree and `frontend/AGENTS.md` for local rules.

## Working with the spec-kit workflow

This project uses spec-kit slash commands (available as skills: `speckit-specify`, `speckit-plan`, `speckit-tasks`, `speckit-implement`, `speckit-clarify`, `speckit-checklist`, `speckit-analyze`, `speckit-converge`, `speckit-constitution`) to go from a feature description to working code through review gates: spec → plan → tasks → implement. Follow that flow for new feature work rather than writing code ad hoc, and check `.specify/memory/constitution.md` for the ratified principles before starting.

## Product context (from the PRD)

**Product:** "AnkiHub Brasil" — a web platform for Brazilian "concurseiro" (civil-service exam) students to collaboratively publish, discuss, and correct Anki flashcard decks, syncing changes back to each user's local Anki via a native add-on. Modeled closely on the real AnkiHub product's API/UX conventions (cursor pagination with `next`, trailing-slash routes, `AnkiHub_Protect::<field>` tag convention, bulk change suggestions).

**Planned architecture** (see PRD §4.1–4.3):

```
[Anki Desktop + Add-on] <--HTTPS/API--> [Backend Django + DRF] <--> [Postgres via Supabase]
                                               |        |
                                          [Auth: Supabase Auth]   [Media: Supabase Storage/S3]
                                               |
[Web App Next.js/React] <-----HTTPS/API-------+
```

- **Backend:** Django + Django REST Framework — chosen to mirror the real AnkiHub backend's observed API conventions rather than reinvent them.
- **Frontend:** Next.js/React.
- **DB:** Postgres via Supabase, provisioned in the **US East (Virginia)** region (not São Paulo) to stay co-located with the backend on Heroku; auth via Supabase Auth (not DRF's native `TokenAuthentication`).
- **Media:** Supabase Storage (S3-compatible, pre-signed URLs).
- **Add-on:** Python, using Anki's native `aqt`/`anki` libraries.
- **Backend compute hosting:** **Heroku**, decided for year 1 to use already-available credits (~1 year of dyno cost covered); no Heroku Postgres add-on — the dyno connects straight to Supabase's pooled connection string (`DATABASE_URL` via Supavisor). Heroku's Common Runtime has no São Paulo region, which is why the DB region above follows it to the US instead of the user base — co-locating backend and DB cuts more latency than co-locating DB and end user, since a page can fire several sequential queries. Revisit hosting (Railway/Render/Fly.io, or paid Heroku) once the credits run out — cost stops being zero at that point (~$5/mo minimum on a paid Eco dyno).

**Core domain flows** (see PRD §4.1 and user stories US-05 through US-10 for full detail):
1. **Publish:** moderator creates/imports a deck via the add-on → uploads via API → backend persists decks/notes/note-types in a schema that maps 1:1 to Anki's native SQLite tables (`notes`, `notetypes`, `templates`, `fields`, `cards`, `col`) so a local collection can be deterministically reconstructed.
2. **Subscribe/sync:** user subscribes on the web → add-on syncs deltas since the last locally-cached `mod` timestamp, applying changes in a fixed order (note types → notes → subdeck reorg), respecting per-user protected fields/tags (US-12), and falling back to a full deck resync if a delta isn't safely reconcilable (e.g., note type structure changed).
3. **Suggest → moderate → propagate:** users submit change/new-note/delete suggestions (categorized, with required justification) → visible to all subscribers on the "Community Suggestions" screen with like/dislike and per-suggestion discussion threads → a moderator (a deck can have multiple, all equal-permission) accepts/rejects → accepted changes update the official note and enter the sync queue for all subscribers.

**Notable constraints that should shape implementation choices:**
- After a one-time authenticated import into a nonexistent deck, sync is **unidirectional** (web is always the source of truth); the add-on cannot republish or push later local edits back — this is the deliberate mitigation for merge-conflict risk (PRD §5.2).
- Rich-text (WYSIWYG) fields store raw HTML compatible with native Anki fields — **must be sanitized server-side** (allowlist tags/attributes, no `<script>`/inline handlers) before persisting or rendering, this is a called-out stored-XSS risk.
- LGPD compliance requirements are specific: separate opt-in consent (not pre-checked) for marketing emails vs. research data use, 7-day grace period on account deletion, and JSON data export on request (US-13).
- AI features (smart search, study chatbot) are explicitly out of scope until v2.0 — don't introduce LLM/AI dependencies for MVP work.
- Full non-goals list is in PRD §2.3 — check it before adding scope (e.g., no real-time collaborative editing, no moderator hierarchy, no private/invite-only decks, no monetization).
