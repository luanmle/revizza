<!--
Sync Impact Report
==================
Current amendment:
  - Version change: 1.2.1 to 1.3.0 (minor — new Principle VIII added).
  - Added Principle VIII. Sync Fidelity & State Separation: AnkiHub-grade
    sync fidelity as a collaborative content repository; strict domain
    separation between Note Content (schemas/note-type/fields/media/tags)
    and Card State (scheduling metadata: ease, intervals, due dates, local
    review history); sync/pull from the platform MUST touch only Note
    Content, never overwrite/reset/corrupt local scheduling or review
    progress; every `/speckit.plan` touching note/deck data models, sync
    endpoints, or note/deck business rules MUST address this separation
    explicitly and include automated-test tasks proving payload updates
    don't affect local study metadata.
  - Modified sections: Governance → Compliance review list now includes
    Principle VIII alongside II/III/IV as a hard gate for PRs touching
    sync, note/deck data models, or scheduling-adjacent code.
  - ✅ `.specify/templates/plan-template.md`: no change needed (the
    Constitution Check gate reads this file dynamically).
  - ✅ `.specify/templates/spec-template.md`: no change needed.
  - ✅ `.specify/templates/tasks-template.md`: no change needed (task
    categorization already supports adding test tasks per plan; the new
    principle's test requirement is enforced via the Constitution Check
    gate at plan time, not a template structure change).
  - ✅ `CLAUDE.md`: version and principle count updated.
  - Note: no backend model currently stores card-scheduling state (`Note`
    in `backend/apps/notes/models.py` has no ease/interval/due fields —
    scheduling lives exclusively in the local Anki SQLite `cards`/`revlog`
    tables); this amendment codifies that existing invariant explicitly
    rather than changing current behavior.

Previous amendment (historical):
  - Version change: 1.2.0 to 1.2.1 (patch — typo fix in Principle I: the
    protection-tag convention now reads `AnkiHubBR_Protect::<Campo>`,
    matching Principle II, spec.md FR-041, and the add-on code; no
    semantic change).
  - ✅ `CLAUDE.md`: stale `AnkiHub_Protect::<field>` form corrected.

Previous amendment (historical):
  - Version change: 1.1.0 to 1.2.0 (minor — Principle II materially clarified).
  - Modified Principle II to permit exactly one authenticated initial import
    into a nonexistent deck and forbid add-on republication afterward.
  - Added/removed sections: none.
  - ✅ `.specify/templates/plan-template.md`, `spec-template.md`, and
    `tasks-template.md`: no changes needed.
  - ✅ `specs/001-ankihub-brasil-mvp/plan.md`, `contracts/sync.md`,
    `quickstart.md`, and `tasks.md`: initial-import boundary propagated.
  - ✅ `CLAUDE.md`: constitution version and sync constraint updated.
  - ✅ `PRD-AnkiHub-Brasil.md`: already distinguishes initial import from sync.

Previous amendment (historical):
Version change: 1.0.1 → 1.1.0 (minor — two new principles added)
Modified principles: none renamed/removed
Added sections:
  - Principle VI. Current Docs & Minimal Code (context7 + ponytail)
  - Principle VII. Design Tooling Pipeline (ui-ux-pro-max + impeccable)
Removed sections: none
Modified sections:
  - Technology Constraints — Frontend entry expanded with the styling
    stack ratified on 2026-07-13: Tailwind CSS 4 + shadcn/ui (preset
    base-nova, installed and build-verified in `frontend/`).
Templates requiring updates:
  - ✅ .specify/templates/plan-template.md — no change needed (the
    Constitution Check gate reads this file dynamically).
  - ✅ .specify/templates/spec-template.md — no change needed.
  - ✅ .specify/templates/tasks-template.md — no change needed.
  - ✅ CLAUDE.md — updated in the same pass: removed stale claims that
    the constitution was still an unfilled template.
  - ✅ frontend/AGENTS.md — already aligned (context7/ponytail/styling
    rules recorded there on 2026-07-13, before this amendment).
  - ✅ rascunho-frontend.md — folded into spec-kit artifacts and deleted
    (resolved after the 1.1.0 amendment).
Follow-up TODOs:
  - TODO(NUMERIC_KPIS): MVP success-metric targets in the PRD are marked
    `TBD-valor`; no constitutional gate depends on them yet.
  - TODO(LAUNCH_DEADLINE): No launch deadline has been set by the user
    (PRD §5.3); revisit if a Development Workflow deadline gate is needed.
  - TODO(HOSTING_YEAR2): PRD §5.3 flags a new open decision — revisit
    backend hosting once the Heroku year-1 credits expire (migrate to
    Railway/Render/Fly.io, or move to paid Heroku).
  - ✅ DESIGN_SYSTEM: `frontend/design-system/MASTER.md` generated (T107);
    Principle VII's persistent reference now exists — TODO resolved.
-->

# AnkiHub Brasil Constitution

## Core Principles

### I. Parity Over Reinvention

When a design or API question already has a proven answer in the real
AnkiHub product, adopt that answer instead of designing a novel one. This
applies to API conventions (cursor pagination via `next`, trailing-slash
routes, bulk-suggestion endpoints), the field/tag protection convention
(`AnkiHubBR_Protect::<Campo>`-style tags), the delta-sync ordering (note
types → notes → subdeck reorganization), and stack choices already
confirmed in the PRD (Django + DRF, Supabase-managed auth/storage). A
deviation from an established AnkiHub pattern MUST be justified in the
spec/plan with a concrete reason it doesn't fit this project — "we could
design it differently" is not sufficient justification on its own.

**Rationale**: This is a from-scratch team building a niche product with a
well-documented predecessor. Re-deriving already-solved problems (pagination
schemes, sync protocols, protection conventions) is pure schedule risk with
no compensating benefit to users.

### II. Unidirectional Sync — Web Is the Source of Truth (NON-NEGOTIABLE)

The web platform is always the authoritative source for deck/note content.
The only upstream content operation permitted from the add-on is a one-time
initial import by an authenticated creator into a deck ID that does not yet
exist. That import creates the first official web snapshot atomically and
MUST be rejected if the deck already exists; it MUST NOT republish, merge,
or overwrite local changes afterward. Once the official snapshot exists,
the add-on MUST NOT push local edits back to the backend under any
circumstance in the MVP: all content changes flow web → Anki local only via
the suggestion → moderation → sync-queue pipeline. Locally protected fields
and tags (per-deck configuration or the `AnkiHubBR_Protect::<Campo>` tag
convention) are the only content a sync operation may leave untouched.
When a delta is structurally too large to reconcile safely (e.g. a note
type's template count changed), the add-on MUST fall back to a full deck
resync rather than partially applying the delta.

**Rationale**: This is the explicitly identified mitigation (PRD §5.2) for
the highest-impact technical risk in the product: sync conflicts that could
corrupt, duplicate, or silently delete a user's local notes and spaced-
repetition history. The create-only initial import has no existing official
state to merge with; allowing any later upstream write would reintroduce the
same conflict risk and is forbidden.

### III. Privacy & LGPD Compliance by Design

Every feature touching personal data MUST satisfy, from first
implementation (not retrofitted later): explicit and separately-grantable
consent for optional data uses (marketing email, anonymized research data)
that is off by default and reversible at any time; a 7-day grace period
before permanent account deletion; and machine-readable (JSON) export of a
user's own data on request. Suggestions, comments, and reports are always
tied to an authenticated author — anonymous submission is out of scope for
the MVP, because moderation and accountability depend on it.

**Rationale**: LGPD compliance is a named legal requirement in the PRD
(§4.4, §5.2), not a nice-to-have, and the product's subject matter
(concurso/legal content, public discussion) makes reports and moderation a
near-certainty from day one.

### IV. Secure by Default

Passwords are never stored in plaintext (hash via the auth provider).
All add-on↔backend and web↔backend traffic MUST use HTTPS exclusively.
Rich-text HTML submitted through the note-suggestion editor (US-05/US-06)
MUST be sanitized server-side with an allowlist of tags/attributes — no
`<script>` tags, no inline event handlers — before it is persisted or
rendered to any other user. Sync and suggestion-submission endpoints MUST
be rate-limited. Concurrent syncs for the same user MUST be blocked to
prevent concurrent-write corruption of the local SQLite collection.

**Rationale**: The rich-text editor intentionally accepts free-form HTML
to stay compatible with native Anki fields, which the PRD explicitly flags
as a stored-XSS attack surface (§4.4, §5.2). Treat that surface as hostile
input by default rather than trusting it because it "looks like" editor
output.

### V. MVP Scope Discipline (YAGNI)

Before adding anything not in an approved user story, check the PRD's
Non-Objectives list (§2.3) first. Features explicitly deferred to v1.1/v2.0
(async task queue, notifications, Optional Tag Groups, moderator hierarchy,
AI-based search/chatbot, monetization, native mobile app, version
history/rollback) MUST NOT be pulled forward into MVP work without an
explicit decision recorded in the spec, because each was deliberately
excluded to keep the MVP shippable. Prefer a managed service already
decided in the stack (Supabase Auth/Storage/DB) over building custom
infrastructure for the same problem.

**Rationale**: The PRD already did the scope-cutting work once, with
reasons per deferred item; re-litigating scope inside implementation work
(rather than at the spec stage) is how MVPs quietly become the full
roadmap.

### VI. Current Docs & Minimal Code (context7 + ponytail)

Code creation MUST consult current library documentation via the context7
MCP before using any library API, rather than relying on memorized
knowledge — the installed versions (Next.js 16, React 19, Tiptap 3, and
the Python stack) are newer than model training data. For Next.js
specifically, the vendored docs in `frontend/node_modules/next/dist/docs/`
take precedence (see `frontend/AGENTS.md`). All code follows the ponytail
discipline: the simplest working solution, native platform features and
standard library before any new dependency, and no speculative
abstractions. Deliberate shortcuts are marked with a `ponytail:` comment
naming the ceiling and upgrade path, and diffs SHOULD pass
`/ponytail-review` before merge (`/ponytail-audit` and `/ponytail-debt`
are available for repo-wide sweeps and the shortcut ledger).

**Rationale**: Wrong-from-memory API usage and over-engineered code are
the two dominant sources of rework in AI-assisted development. This
extends Principle V from *what* is built (scope) to *how* it is built
(implementation style).

### VII. Design Tooling Pipeline (ui-ux-pro-max + impeccable)

UI/UX work MUST flow through the ratified tooling pipeline: the
`ui-ux-pro-max` skills generate the visual foundation (design system,
palette, typography, screen scaffolds — product category: collaborative
study platform for Brazilian concurseiros), and the `impeccable` skill is
the audit and art-direction gate (WCAG AA contrast, visual hierarchy,
removal of generic AI styling) applied to every screen before it ships —
its automatic hook findings on frontend edits are handled, not ignored.
Screens are built on the ratified styling stack (Tailwind 4 + shadcn/ui;
components come from the shadcn registry via MCP rather than being
hand-rolled) and MUST satisfy FR-053: functional at 360px viewport width
with no horizontal scrolling. The persistent design system document
(`design-system/MASTER.md`, once generated) is the visual source of truth
for every new screen.

**Rationale**: The functional spec deliberately leaves visuals undefined;
without a ratified generation→audit pipeline and a persistent design
system, each screen invents its own look and the product accretes
inconsistent, inaccessible UI that later needs wholesale retrofit.

### VIII. Sync Fidelity & State Separation (NON-NEGOTIABLE)

- **AnkiHub-standard sync fidelity**: the system MUST maintain maximum
  compatibility and fidelity with AnkiHub's own sync behavior, so the
  update flow works the way users of a collaborative content repository
  already expect it to (Principle I extended to the sync surface
  specifically) — not a reinvented protocol that happens to move similar
  data.
- **Strict domain separation**: the database architecture and application
  entities MUST rigidly separate **Note Content** (note-type schemas,
  field text, media, tags) from **Card State** (scheduling metadata:
  ease/difficulty, intervals, due dates, and local review history). These
  are different lifecycles owned by different parties — content is
  collaboratively authored and web-authoritative; card state is a private,
  per-user local artifact of the Anki scheduler — and MUST NOT share a
  table, a serializer, or a sync payload that treats them as one concern.
- **Local data protection (scheduling immutability)**: updates received
  from the platform (sync/pull operations) MUST modify Note Content
  exclusively. A user's local scheduling history and review progress MUST
  NEVER be overwritten, reset, or corrupted by a note-type or deck sync —
  including the full-resync fallback path (Principle II) triggered by a
  structural change, which rebuilds note/note-type data but MUST leave
  every local card's scheduling state untouched.
- **Planning governance**: every `/speckit.plan` that creates or modifies
  data models, sync endpoints, or business rules for notes/decks MUST
  explicitly address this separation, and MUST include automated-test
  tasks that specifically assert a payload update does not alter the
  user's local study metadata.

**Rationale**: Principle II already forbids upstream overwrites of
protected fields/tags; this principle closes a related but distinct gap —
even for content a sync operation *is* allowed to update, the scheduling
state riding alongside that content in the same local Anki collection must
never be touched. Conflating "update this note's text" with "touch this
card's review history" is exactly the class of bug that would destroy a
user's spaced-repetition progress silently, which is the single most
trust-destroying failure mode this product can have.

## Technology Constraints

The following stack decisions are ratified in the PRD (§4.3) and MUST be
treated as defaults, not open choices, for new specs/plans:

- **Backend**: Python, Django + Django REST Framework.
- **Frontend**: Next.js (React), styled with Tailwind CSS 4 + shadcn/ui
  (preset base-nova, lucide icons — see `frontend/components.json`;
  ratified 2026-07-13, installed and build-verified).
- **Database**: Postgres via Supabase.
- **Auth**: Supabase Auth (not DRF's native `TokenAuthentication`).
- **Media storage**: Supabase Storage (S3-compatible, pre-signed URLs).
- **Anki add-on**: Python, using the native `aqt`/`anki` libraries.
- **Error tracking**: Sentry (backend and add-on).
- **Backend compute hosting**: Heroku for year 1 (using already-available
  credits covering ~1 year of dyno cost); no Heroku Postgres add-on — the
  dyno connects directly to Supabase's pooled connection string
  (`DATABASE_URL` via Supavisor). The Supabase project is provisioned in
  the US East (Virginia) region rather than São Paulo, specifically to
  stay co-located with Heroku (whose Common Runtime has no São Paulo
  region) — backend↔DB latency matters more here than DB↔end-user
  latency, since a page can fire several sequential queries. This is a
  year-1 decision, not a permanent one: PRD §5.3 flags hosting as a
  decision to revisit once the Heroku credits expire (candidates:
  Railway, Render, Fly.io, or paid Heroku).

A schema change to the core note/deck/card tables MUST remain mappable
1:1 to Anki's native SQLite schema (`notes`, `notetypes`, `templates`,
`fields`, `cards`, `col`) so that a local collection can be deterministically
reconstructed from web-side data (PRD §4.2).

## Development Workflow

Feature work follows the spec-kit cycle already scaffolded in this repo:
`speckit-specify` → `speckit-plan` → `speckit-tasks` → `speckit-implement`,
with `speckit-clarify` used to resolve ambiguity before planning and
`speckit-checklist`/`speckit-analyze` used for pre-implementation review.
Every plan MUST pass a Constitution Check against this document before
Phase 0 research begins, and re-check it after Phase 1 design; violations
require an explicit entry in that plan's Complexity Tracking table
justifying why a simpler, constitution-compliant alternative was rejected.
`PRD-AnkiHub-Brasil.md` remains the authoritative scope document until/
unless a spec explicitly supersedes part of it — specs should reference the
relevant PRD user story (e.g. "US-08") rather than re-describing it.

## Governance

This constitution supersedes ad hoc technical or scope decisions made
during implementation. Any conflict between a spec/plan and this document
MUST be resolved by amending one of the two explicitly, not by silently
deviating in code.

**Amendment procedure**: Amendments are made via the `speckit-constitution`
skill, which regenerates this file, assigns a new version per the
versioning policy below, and propagates a Sync Impact Report identifying
any dependent templates or documents that need matching updates.

**Versioning policy** (semantic versioning applied to governance changes):
- **MAJOR**: Backward-incompatible removal or redefinition of a principle
  (e.g., reversing the unidirectional-sync rule).
- **MINOR**: A new principle or section added, or materially expanded
  guidance on an existing one.
- **PATCH**: Wording clarifications, typo fixes, and non-semantic
  refinements.

**Compliance review**: Every `speckit-plan` run MUST perform the
Constitution Check gate described above. Reviewers of any PR touching
sync, suggestion moderation, personal data, or the rich-text editor should
treat the corresponding principle (II, III, IV) as a hard gate, not a
suggestion. Reviewers of frontend PRs should additionally hold the line on
Principles VI and VII (docs-verified APIs, minimal code, design pipeline).
Reviewers of any PR touching note/deck data models or sync endpoints
should additionally hold the line on Principle VIII (Note Content/Card
State separation, scheduling immutability) as a hard gate.

**Version**: 1.3.0 | **Ratified**: 2026-07-12 | **Last Amended**: 2026-07-14
