# Feature Specification: Add-on Note Actions & Sync Stability

**Feature Branch**: `010-addon-note-actions`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "ADDON — testes de estabilidade da sincronização. Novas features: botão 'Ver no Revizza' no inferior da tela do Anki para o usuário ser redirecionado para aquela nota na web; botão para enviar sugestão de mudança de cartão diretamente pelo Anki ao alterar algum campo, assim como no AnkiHub; botão 'Ver histórico' abre a tela de sugestões de mudanças daquele cartão. Verificar se o sistema permite abrir uma página web da nota no botão 'Ver no Revizza' e possíveis implementações (talvez através de preenchimento do filtro de pesquisa com as informações da nota, como por exemplo o ID)."

## Feasibility Note (verification requested by the user)

The web platform already exposes a dedicated page per note (`/decks/{deck}/notes/{note}`) and the deck notes listing accepts an exact note-ID filter as well as a free-text search term. However, the note page is addressed by the platform's own note identifier, while the add-on identifies notes locally by their stable Anki GUID. Opening a note from Anki therefore requires the system to resolve a locally-known identifier (the note GUID) to the note's web address — either by a direct lookup or by pre-filling the notes search with an identifier the platform understands. This resolution capability is treated as a requirement of this feature (FR-004).

## Clarifications

### Session 2026-07-15

- Q: How should Anki resolve a locally-known note (its GUID) to its web page? → A: A backend endpoint accepts the note GUID and issues an HTTP redirect to the note's page (`/go/note/{guid}` → `/decks/{deckId}/notes/{noteId}`; `/go/note/{guid}/history` → the note's suggestions view). The add-on keeps no GUID→URL mapping.
- Q: What defines that a note "differs from official" before submitting a from-Anki suggestion? → A: Compare local field values against the official version cached at last sync (offline, no network round-trip at submit).
- Q: Do the note/history web pages require web login when opened from Anki? → A: No — these are public read-only pages; contributing (writing suggestions/comments) still requires login.
- Q: Where should the sync stability test suite run? → A: Both — an automated mocked-collection suite in CI plus a documented manual test matrix run against a real Anki profile before release.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open a note on Revizza from Anki (Priority: P1)

While studying or browsing a card in Anki that belongs to a subscribed Revizza deck, the user clicks a "Ver no Revizza" button at the bottom of the Anki screen and their web browser opens directly on that note's page on the platform, where they can read its discussion, suggestions, and details.

**Why this priority**: It is the bridge between the local study experience and the collaborative platform. Every other add-on action in this feature (suggesting a change, viewing history) becomes discoverable once the user can jump from a card to its web page.

**Independent Test**: With a synced deck, open one of its cards in Anki, click "Ver no Revizza", and confirm the browser lands on the page of that exact note.

**Acceptance Scenarios**:

1. **Given** a card from a subscribed Revizza deck is displayed in Anki, **When** the user clicks "Ver no Revizza", **Then** the default web browser opens on that note's page on the platform.
2. **Given** a card that does not belong to any Revizza deck is displayed, **When** the user looks at the bottom of the screen, **Then** the "Ver no Revizza" action is absent or disabled.
3. **Given** the note exists locally but can no longer be found on the platform (e.g., removed from the official deck), **When** the user clicks "Ver no Revizza", **Then** the user is informed the note was not found instead of landing on an error page.

---

### User Story 2 - Suggest a card change directly from Anki (Priority: P2)

The user edits one or more fields of a card from a subscribed deck inside Anki's editor and, without leaving Anki, clicks a button to submit those edits as a change suggestion to the community — providing the required category and justification, exactly as they would on the web.

**Why this priority**: Removes the biggest friction in the contribution loop (spotting an error while studying, then having to find the note on the web and retype the fix). It depends on the same note resolution as User Story 1, so it builds on it.

**Independent Test**: Edit a field of a synced note in Anki, submit a suggestion from the editor, and confirm the suggestion appears on the deck's Community Suggestions screen on the web with the edited content, category, and justification.

**Acceptance Scenarios**:

1. **Given** the user modified at least one field of a note from a subscribed deck, **When** they trigger the suggest action, **Then** they are asked for a change category and a justification before submission.
2. **Given** a valid category and justification were provided, **When** the suggestion is submitted, **Then** it appears in the deck's Community Suggestions on the web, showing the proposed field values, and the user receives a confirmation in Anki.
3. **Given** the note's local content is identical to the official version, **When** the user triggers the suggest action, **Then** they are informed there is nothing to suggest.
4. **Given** the submission fails (offline, expired session, rejected by the platform), **When** the user submits, **Then** their edits and form input are preserved and a clear error explains what to do.
5. **Given** the user is not signed in through the add-on, **When** they trigger the suggest action, **Then** they are prompted to sign in first.

---

### User Story 3 - View a card's suggestion history from Anki (Priority: P3)

While viewing a card in Anki, the user clicks "Ver histórico" and their browser opens the platform's suggestions screen already filtered to that card's note, showing all past and pending change suggestions for it.

**Why this priority**: Valuable for transparency (why did this card change? is a fix already pending?) but consumes the same navigation capability as User Story 1, with lower everyday frequency.

**Independent Test**: For a note with at least one suggestion, click "Ver histórico" in Anki and confirm the browser opens the suggestions screen listing only that note's suggestions.

**Acceptance Scenarios**:

1. **Given** a card from a subscribed deck with existing suggestions, **When** the user clicks "Ver histórico", **Then** the browser opens the suggestions screen filtered to that note.
2. **Given** a note with no suggestions yet, **When** the user clicks "Ver histórico", **Then** the browser opens the same screen showing an empty state for that note (not an error).

---

### User Story 4 - Sync remains stable under adverse conditions (Priority: P2)

A user syncs their subscribed decks repeatedly, under interruptions, and across content edge cases, and their local collection always ends in a correct, consistent state — never with duplicated notes, lost scheduling, or a partially-applied update.

**Why this priority**: The three new actions above all assume the local collection faithfully mirrors the platform. Stability evidence for sync protects everything else and was explicitly requested.

**Independent Test**: Execute a repeatable stability test suite covering repeated syncs, interrupted syncs, and content edge cases, and confirm every run ends with a consistent collection.

**Acceptance Scenarios**:

1. **Given** an up-to-date subscribed deck, **When** the user syncs multiple times in a row with no remote changes, **Then** no local changes occur (sync is idempotent).
2. **Given** a sync is interrupted mid-way (connection drop, application close), **When** the user syncs again, **Then** the collection converges to the correct final state with no duplicated or orphaned notes.
3. **Given** remote changes include edge-case content (empty fields, very large fields, special characters, notes moved between subdecks, note type structure changes), **When** the user syncs, **Then** all changes apply correctly or the documented full-resync fallback is triggered — never a partial corrupt state.
4. **Given** any sync outcome, **When** the sync finishes, **Then** the user's card scheduling (due dates, intervals, review history) is untouched, and protected fields/tags remain preserved.

---

### Edge Cases

- Card shown in Anki belongs to a Revizza deck, but the deck subscription was cancelled on the web: actions should detect this and inform the user rather than fail silently.
- Note was created locally by the user (never part of the official deck): "Ver no Revizza" and "Ver histórico" must not appear as available.
- User edits several notes in bulk in Anki: the from-Anki suggestion flow covers the single note currently open; bulk suggestions remain a web flow.
- The platform is unreachable when a button is clicked: the user gets a clear offline message; nothing hangs the Anki interface.
- The user's session in the add-on expired: navigation actions still work (the web pages are viewable), but suggestion submission prompts for sign-in.
- The same note appears in multiple subscribed decks: actions target the deck the note was synced from.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Anki add-on MUST display a "Ver no Revizza" action at the bottom of the card review screen when the displayed card's note belongs to a subscribed Revizza deck, and MUST hide or disable it otherwise.
- **FR-002**: Activating "Ver no Revizza" MUST open the user's default web browser on the platform page of that exact note.
- **FR-003**: The add-on MUST offer a "Ver histórico" action for the same set of cards, which opens the platform's suggestions screen filtered to that note.
- **FR-004**: The system MUST provide a backend endpoint that accepts a note's stable GUID (the identifier shared between the local collection and the platform) and issues an HTTP redirect to that note's web page (e.g., `/go/note/{guid}` → `/decks/{deckId}/notes/{noteId}`). When the GUID resolves to no live note (removed from the official deck), the browser-facing redirect MUST land the user on a friendly "nota não encontrada" web page — never a raw JSON/HTTP error page (US1 AS#3). The add-on links to this GUID-addressed endpoint and holds no local GUID→URL mapping.
- **FR-005**: The note's suggestion history MUST be reachable through a GUID-addressed backend redirect (e.g., `/go/note/{guid}/history`) that resolves to the platform's suggestions view already filtered to that note, so the add-on can deep-link to it.
- **FR-005a**: The note page and the note-filtered suggestions view reached by these redirects MUST be readable without web login (public read-only); only contributing (submitting suggestions/comments) requires authentication.
- **FR-006**: The add-on MUST offer, in the note editor, an action to submit the current local field values of a note from a subscribed deck as a change suggestion, requiring a change category and a written justification before submission (same rules as the web flow).
- **FR-007**: A suggestion submitted from Anki MUST be indistinguishable from one submitted on the web: it appears on the deck's Community Suggestions screen, is attributed to the signed-in user, and follows the same moderation flow.
- **FR-008**: Before submitting, the add-on MUST compare the local field values against the official version cached at the last sync; if they are identical, it MUST inform the user ("nada a sugerir") and MUST NOT submit an empty suggestion. The check MUST work offline without a submit-time network round-trip.
- **FR-009**: When a from-Anki suggestion submission fails for any reason, the add-on MUST preserve the user's input, report the failure in plain language, and never block or freeze the Anki interface.
- **FR-010**: Suggestion submission from Anki MUST require an authenticated add-on session; navigation actions ("Ver no Revizza", "Ver histórico") MUST NOT require one, and the pages they open MUST be viewable without web login (see FR-005a).
- **FR-011**: The sync process MUST be idempotent: syncing an already up-to-date deck produces no local changes.
- **FR-012**: After an interrupted sync, a subsequent sync MUST converge the local collection to the correct state with no duplicated, missing, or orphaned notes.
- **FR-013**: Sync MUST never modify card scheduling data or user-protected fields/tags, under any of the stability scenarios exercised.
- **FR-014**: The project MUST include an automated, repeatable sync stability test suite that runs against a mocked/in-memory collection in CI, covering at minimum: repeated syncs, interrupted/resumed syncs, content edge cases (empty/large/special-character fields), subdeck moves, and note type structure changes triggering the full-resync fallback.
- **FR-014a**: The project MUST also include a documented manual test matrix, executed against a real Anki profile before release, covering the same stability scenarios that cannot be faithfully reproduced in the mocked suite.

### Key Entities

- **Note identity mapping**: the association between a note in the local collection (stable GUID) and its record on the platform (platform note identifier and owning deck). It lives server-side and is resolved on demand by the GUID-addressed redirect endpoint (FR-004/FR-005); the add-on holds no local copy of it.
- **Change suggestion (from Anki)**: same entity as a web-submitted suggestion — proposed field values, category, justification, author — with no distinct type or flag.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a card displayed in Anki, a user reaches that note's web page in one click and under 5 seconds, with the correct note shown on the first attempt in 100% of tested cases.
- **SC-002**: A user can go from spotting an error on a card in Anki to a submitted change suggestion without leaving Anki, in under 2 minutes.
- **SC-003**: Suggestions submitted from Anki are accepted by the platform and visible on the Community Suggestions screen in 100% of valid submissions in testing.
- **SC-004**: The sync stability suite passes 100% of its scenarios on every run, and 20 consecutive syncs of an unchanged deck produce zero local modifications.
- **SC-005**: Zero occurrences of scheduling data loss or protected-field overwrites across the entire stability test matrix.

## Assumptions

- "Ver no Revizza" and "Ver histórico" live on the card review screen's bottom bar (that is the "inferior da tela" in Anki); the suggest-change action lives in the note editor, where field edits happen — mirroring the referenced AnkiHub behavior.
- "Histórico" means the note's change-suggestion history on the existing Community Suggestions screen (filtered to the note), not a new dedicated screen.
- The from-Anki suggestion flow targets a single note (the one open in the editor); bulk suggestions remain web-only, per current scope.
- The note GUID is the shared stable identifier between local collections and the platform (it already drives sync), so it is the key the backend redirect endpoint resolves; the add-on only needs to know a note's GUID and the platform base URL to build a link.
- Navigation actions open the platform in the system's default browser; no embedded web view is introduced.
- Unidirectional sync is unchanged: a from-Anki suggestion is a proposal into the moderation flow, never a direct write to the official deck.
- Button visibility keys off the local sync cache (the note's GUID is present with a deck), not a live subscription check. If a user cancels a deck subscription on the web but the note still exists locally, the navigation buttons remain visible and clicking them opens the still-public note/suggestions page — an acceptable outcome, so no live-subscription round-trip is added (YAGNI). The suggest action still requires an authenticated session (FR-010); moderation of a non-subscriber's suggestion is a platform-side concern, unchanged.
