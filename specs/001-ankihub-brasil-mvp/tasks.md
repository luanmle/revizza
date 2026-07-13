# Tasks: AnkiHub Brasil — MVP

**Input**: Design documents from `/specs/001-ankihub-brasil-mvp/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Incluídas — `plan.md` já define `tests/contract/` mapeado 1:1 aos arquivos em `contracts/`, então os testes de contrato fazem parte do escopo, não são opcionais aqui.

**Organization**: Tarefas agrupadas por user story (spec.md), em ordem de prioridade (P1 → P2 → P3), não pela numeração original de US no PRD.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: A qual user story do spec.md a tarefa pertence (US1..US13)
- Caminhos de arquivo exatos em cada descrição, seguindo a estrutura de `plan.md`

---

## Phase 1: Setup

**Purpose**: Inicialização dos três projetos (backend, frontend, add-on)

- [X] T001 Create `backend/`, `frontend/`, `addon/` project skeletons per plan.md Project Structure
- [X] T002 [P] Initialize `backend/` Django project with dependencies (Django, DRF, django-ratelimit, nh3, supabase-py, Pillow, factory_boy) in `backend/requirements.txt` and `backend/config/`
- [X] T003 [P] Initialize `frontend/` Next.js (App Router) project with dependencies (React, Tiptap, TanStack Query) in `frontend/package.json`
- [X] T004 [P] Initialize `addon/ankihub_br/` package skeleton (`manifest.json`, `config.json`, `entry_point.py` stubs) with dependencies (peewee, requests, pytest-anki) in `addon/requirements.txt`
- [X] T005 [P] Configure linting/formatting: ruff+black for `backend/` and `addon/`, eslint+prettier for `frontend/`
- [X] T006 [P] Configure test runners: pytest+pytest-django+factory_boy in `backend/`, Vitest+Playwright in `frontend/`, pytest puro + `anki.collection.Collection` headless in `addon/` (pytest-anki 1.0.0b7 é PyQt5-only, incompatível com anki>=25 — ver `addon/requirements.txt`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura core que TODA user story depende

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase estar completa

- [X] T007 Configure Django settings (base/dev/prod) with Supabase Postgres `DATABASE_URL` and Supabase Auth token verification in `backend/config/settings/`
- [X] T008 [P] Configure DRF default `CursorPagination` and `Accept`-header API versioning scheme in `backend/config/settings/`
- [X] T009 [P] Configure `django-ratelimit` defaults for sync and suggestion endpoints in `backend/config/`
- [X] T010 [P] Implement shared `nh3` HTML sanitization utility in `backend/apps/notes/sanitize.py`
- [X] T011 Create User profile model (`target_career`, `target_board`, consents, `is_suspended`, `deletion_requested_at`) in `backend/apps/accounts/models.py`
- [X] T012 Create Deck, DeckModerator, NoteType, Note core models in `backend/apps/catalog/models.py` and `backend/apps/notes/models.py`
- [X] T013 [P] Configure Sentry error tracking in `backend/config/` and `addon/ankihub_br/`
- [X] T014 [P] Set up frontend API client with Supabase auth token handling in `frontend/src/lib/api-client.ts`
- [X] T015 [P] Set up add-on HTTP client skeleton (auth header, retry/backoff) in `addon/ankihub_br/ankihub_br_client/`
- [X] T016 Set up add-on peewee/SQLite `SyncStateCache` schema in `addon/ankihub_br/db/`

**Checkpoint**: Fundação pronta — user stories podem começar

---

## Phase 3: User Story 1 - Cadastro, login e consentimentos (Priority: P1) 🎯 MVP

**Goal**: Estudante se cadastra, faz login e controla consentimentos LGPD desde o primeiro acesso (FR-001 a FR-005).

**Independent Test**: Criar conta nova, confirmar e-mail, logar, verificar que os dois consentimentos começam desmarcados e podem ser alterados em "Minha conta".

### Tests for User Story 1

- [X] T017 [P] [US1] Contract test `POST /api/v1/accounts/register/` in `backend/tests/contract/test_accounts_register.py`
- [X] T018 [P] [US1] Contract test `GET /accounts/me/`, `PATCH /accounts/me/consents/` in `backend/tests/contract/test_accounts_me.py`
- [X] T019 [P] [US1] Integration test cadastro→login→alterar consentimento in `backend/tests/integration/test_registration_flow.py`

### Implementation for User Story 1

- [X] T020 [US1] Implement register + password-reset endpoints wrapping Supabase Auth in `backend/apps/accounts/views.py`
- [X] T021 [US1] Implement `GET /accounts/me/` and `PATCH /accounts/me/consents/` endpoints in `backend/apps/accounts/views.py`
- [X] T022 [P] [US1] Build cadastro/login/onboarding pages (carreira/banca opcionais) in `frontend/src/app/(auth)/`
- [X] T023 [P] [US1] Build consent toggles on account screen (desmarcados por padrão) in `frontend/src/app/account/page.tsx`

**Checkpoint**: US1 funcional e testável isoladamente

---

## Phase 4: User Story 2 - Exploração e assinatura do catálogo de decks (Priority: P1)

**Goal**: Estudante navega o catálogo, filtra por matéria e se inscreve em um deck (FR-006 a FR-009).

**Independent Test**: Abrir catálogo, aplicar filtro de tag, clicar "Inscrever-se" e confirmar o vínculo criado.

### Tests for User Story 2

- [X] T024 [P] [US2] Contract test `GET /api/v1/decks/` list/filter/recommend in `backend/tests/contract/test_catalog_list.py`
- [X] T025 [P] [US2] Contract test subscribe/unsubscribe/update-preferences in `backend/tests/contract/test_catalog_subscriptions.py`

### Implementation for User Story 2

- [X] T026 [US2] Implement Deck list/detail/filter/recommendation endpoints in `backend/apps/catalog/views.py`
- [X] T027 [US2] Implement Subscription model + subscribe/unsubscribe/preferences endpoints in `backend/apps/catalog/models.py`, `views.py`
- [X] T028 [P] [US2] Build catálogo page with filter and recommendation sort in `frontend/src/app/decks/page.tsx`
- [X] T029 [P] [US2] Build deck detail page with "Inscrever-se" button in `frontend/src/app/decks/[id]/page.tsx`

**Checkpoint**: US1 + US2 funcionam juntos e isoladamente

---

## Phase 5: User Story 3 - Sincronização do deck local via add-on (Priority: P1)

**Goal**: Deck assinado chega e se mantém atualizado no Anki local, respeitando rate limit, backup e fallback de resync completo (FR-031 a FR-039).

**Independent Test**: Assinar um deck, disparar sync manual pelo add-on, confirmar notas na coleção local; disparar duas sincronizações seguidas e confirmar bloqueio por rate limit.

### Tests for User Story 3

- [X] T030 [P] [US3] Contract test `GET /decks/{id}/sync/delta/` in `backend/tests/contract/test_sync_delta.py`
- [X] T031 [P] [US3] Contract test `GET /decks/{id}/sync/full/` in `backend/tests/contract/test_sync_full.py`
- [X] T032 [P] [US3] Contract test `GET /media/{content_hash}/` in `backend/tests/contract/test_sync_media.py`
- [X] T033 [P] [US3] pytest-anki test: aplicação do delta na ordem tipos de nota→notas→subdecks in `addon/tests/unit/test_delta_apply.py`
- [X] T034 [P] [US3] pytest-anki test: backup + rollback em sincronização interrompida in `addon/tests/unit/test_sync_failure_recovery.py`

### Implementation for User Story 3

- [X] T035 [US3] Implement deck publish (upload inicial) endpoint in `backend/apps/sync/views.py`
- [X] T036 [US3] Implement delta endpoint (`since_mod`, `full_resync_required`) in `backend/apps/sync/views.py`
- [X] T037 [US3] Implement full-resync endpoint in `backend/apps/sync/views.py`
- [X] T038 [US3] Implement media hash-dedup endpoint with Supabase Storage signed URLs in `backend/apps/sync/media.py`
- [X] T039 [US3] Apply 10s rate limit to sync endpoints in `backend/apps/sync/views.py`
- [X] T040 [US3] Implement add-on delta-apply logic (tipos de nota→notas→subdecks) in `addon/ankihub_br/main/sync.py`
- [X] T041 [US3] Implement add-on backup-before-sync and rollback-on-failure in `addon/ankihub_br/main/backup.py`
- [X] T042 [US3] Implement add-on full-resync fallback trigger in `addon/ankihub_br/main/sync.py`
- [X] T043 [US3] Implement three sync triggers (manual, `profile_did_open`, encadeado via monkey-patch em `AnkiQt._sync_collection_and_media`) in `addon/ankihub_br/gui/` and `addon/ankihub_br/entry_point.py`
- [X] T044 [US3] Implement add-on media sync with content-hash dedup in `addon/ankihub_br/main/media.py`
- [X] T045 [US3] Implement LTS-only version check + `X-Anki-Version` header in `addon/ankihub_br/main/compat.py`

**Checkpoint**: US1+US2+US3 entregam o loop completo de onboarding→sync (quickstart cenário 1)

---

## Phase 6: User Story 4 - Sugestão de mudança em nota existente (Priority: P1)

**Goal**: Estudante sugere correção em nota existente com editor rich text e diff visual (FR-013 a FR-017).

**Independent Test**: Abrir nota, preencher tipo de mudança + justificativa, editar campo via Tiptap, enviar e confirmar sugestão `pending` vinculada à nota.

### Tests for User Story 4

- [X] T046 [P] [US4] Contract test `POST /notes/{id}/suggestions/change/` in `backend/tests/contract/test_suggestions_change.py`
- [X] T047 [P] [US4] Contract test `POST /suggestions/bulk-change/` in `backend/tests/contract/test_suggestions_bulk.py`

### Implementation for User Story 4

- [X] T048 [US4] Create Suggestion, SuggestionTargetNote models in `backend/apps/suggestions/models.py`
- [X] T049 [US4] Apply `nh3` sanitization to `proposed_field_values` in `backend/apps/suggestions/serializers.py`
- [X] T050 [US4] Implement change-suggestion and bulk-change endpoints in `backend/apps/suggestions/views.py`
- [X] T051 [P] [US4] Build Tiptap rich-text editor with raw-HTML toggle in `frontend/src/components/RichTextEditor.tsx`
- [X] T052 [P] [US4] Build suggest-change form with side-by-side diff viewer in `frontend/src/app/decks/[id]/notes/[noteId]/suggest/page.tsx`
- [X] T053 [P] [US4] Build bulk-suggestion note-selection UI in `frontend/src/app/decks/[id]/suggest-bulk/page.tsx`

**Checkpoint**: US4 funciona isoladamente sobre US1-US3

---

## Phase 7: User Story 5 - Tela de Community Suggestions e decisão de moderação (Priority: P1)

**Goal**: Qualquer assinante vê/vota/discute sugestões; moderador aceita ou rejeita (FR-020 a FR-027).

**Independent Test**: Ver sugestão criada em US4 na tela de Community Suggestions, curtir com outro usuário, aceitar como moderador e confirmar que a nota oficial muda.

### Tests for User Story 5

- [ ] T054 [P] [US5] Contract test `GET /decks/{id}/suggestions/` filters in `backend/tests/contract/test_suggestions_list.py`
- [ ] T055 [P] [US5] Contract test votes/comments/accept/reject in `backend/tests/contract/test_suggestions_moderation.py`

### Implementation for User Story 5

- [ ] T056 [US5] Create SuggestionVote model in `backend/apps/suggestions/models.py`
- [ ] T057 [US5] Create Comment model (nota XOR sugestão FK) in `backend/apps/discussions/models.py`
- [ ] T058 [US5] Implement suggestion list/filter/detail endpoints in `backend/apps/suggestions/views.py`
- [ ] T059 [US5] Implement vote upsert endpoints in `backend/apps/suggestions/views.py`
- [ ] T060 [US5] Implement suggestion-comment thread endpoints in `backend/apps/suggestions/views.py`
- [ ] T061 [US5] Implement accept endpoint (aplica na Note oficial, enfileira sync) in `backend/apps/suggestions/decisions.py`
- [ ] T062 [US5] Implement reject endpoint with `rejection_reason` in `backend/apps/suggestions/decisions.py`
- [ ] T063 [US5] Enforce moderator-only permission on accept/reject in `backend/apps/suggestions/permissions.py`
- [ ] T064 [P] [US5] Build Community Suggestions screen (3 abas, filtros, votos, thread) in `frontend/src/app/decks/[id]/suggestions/page.tsx`
- [ ] T065 [P] [US5] Build moderator accept/reject controls in `frontend/src/components/SuggestionModerationControls.tsx`

**Checkpoint**: 🎯 Fatia P1 completa — MVP demonstrável ponta-a-ponta (quickstart cenário 2)

---

## Phase 8: User Story 6 - Inspeção e busca de notas (Priority: P2)

**Goal**: Buscar notas por termo/ID com renderização fiel ao Anki, em <500ms (FR-010, FR-011).

**Independent Test**: Buscar termo presente em um campo e por ID exato num deck de teste; confirmar tempo de resposta e fidelidade do template/CSS.

- [ ] T066 [P] [US6] Contract test `GET /decks/{id}/notes/` search in `backend/tests/contract/test_notes_search.py`
- [ ] T067 [US6] Implement note search (texto+ID, <500ms) and detail endpoints in `backend/apps/notes/views.py`
- [ ] T068 [P] [US6] Build note search UI and faithful template/CSS renderer in `frontend/src/app/decks/[id]/notes/page.tsx`

**Checkpoint**: US6 funciona isoladamente

---

## Phase 9: User Story 7 - Discussão geral na nota (Priority: P2)

**Goal**: Comentários públicos por nota, distintos da thread de sugestão (FR-012).

**Independent Test**: Comentar em uma nota, editar/excluir o próprio comentário, confirmar que não aparece na thread de nenhuma sugestão daquela nota.

- [ ] T069 [P] [US7] Contract test note comments CRUD in `backend/tests/contract/test_note_comments.py`
- [ ] T070 [US7] Implement note comment create/edit/delete-own endpoints in `backend/apps/discussions/views.py`
- [ ] T071 [P] [US7] Build note comment thread UI in `frontend/src/components/CommentThread.tsx`

**Checkpoint**: US7 funciona isoladamente

---

## Phase 10: User Story 8 - Sugestão de nota nova (Priority: P2)

**Goal**: Propor nota inteiramente nova com todos os campos do tipo de nota (FR-018).

**Independent Test**: Preencher formulário de nota nova deixando um campo vazio, enviar e confirmar que aparece na aba própria de Community Suggestions com o campo vazio sinalizado.

- [ ] T072 [P] [US8] Contract test `POST /decks/{id}/suggestions/new-note/` in `backend/tests/contract/test_suggestions_new_note.py`
- [ ] T073 [US8] Implement new-note suggestion endpoint with empty-field flagging in `backend/apps/suggestions/views.py`
- [ ] T074 [P] [US8] Build new-note suggestion form (todos os campos do tipo de nota + rich text) in `frontend/src/app/decks/[id]/suggest-new-note/page.tsx`

**Checkpoint**: US8 funciona isoladamente

---

## Phase 11: User Story 9 - Sugestão de exclusão de nota (Priority: P2)

**Goal**: Sugerir remoção de nota, propagada na sincronização seguinte (FR-019, FR-037).

**Independent Test**: Sugerir exclusão com justificativa, aceitar como moderador, sincronizar e confirmar remoção/marcação conforme preferência do assinante.

- [ ] T075 [P] [US9] Contract test `POST /notes/{id}/suggestions/deletion/` in `backend/tests/contract/test_suggestions_deletion.py`
- [ ] T076 [US9] Implement deletion-suggestion endpoint and accept-path soft-delete propagation in `backend/apps/suggestions/views.py`, `decisions.py`
- [ ] T077 [P] [US9] Build deletion-suggestion form and confirmation UI in `frontend/src/app/decks/[id]/notes/[noteId]/suggest-deletion/page.tsx`

**Checkpoint**: US9 funciona isoladamente

---

## Phase 12: User Story 11 - Proteção de campos e tags pessoais (Priority: P2)

**Goal**: Conteúdo pessoal protegido nunca é sobrescrito pela sincronização (FR-040 a FR-044).

**Independent Test**: Configurar campo protegido, adicionar tag `AnkiHubBR_Protect::Campo` a uma nota, sincronizar após uma mudança aceita e confirmar que o conteúdo protegido permanece intacto.

- [ ] T078 [P] [US11] Contract test `GET`/`PUT /decks/{id}/protection/me/` in `backend/tests/contract/test_protection.py`
- [ ] T079 [P] [US11] pytest-anki test: campo/tag protegido preservado ao aplicar delta in `addon/tests/unit/test_protection.py`
- [ ] T080 [US11] Create ProtectedFieldConfig/ProtectedTagConfig models and endpoints in `backend/apps/protection/models.py`, `views.py`
- [ ] T081 [US11] Implement add-on protection lookup before delta apply (config de deck + tag `AnkiHubBR_Protect::<Campo>`) in `addon/ankihub_br/protection/`
- [ ] T082 [US11] Implement guard against touching other add-ons' internal tags (`leech`, `marked`) in `addon/ankihub_br/protection/`
- [ ] T083 [P] [US11] Build protection config UI (lista de campos/tags por deck) in `frontend/src/app/decks/[id]/protection/page.tsx`

**Checkpoint**: 🎯 Fatia P2 completa

---

## Phase 13: User Story 10 - Convite de co-moderador (Priority: P3)

**Goal**: Moderador convida outro usuário para dividir a curadoria; deck nunca fica sem moderador (FR-028 a FR-030).

**Independent Test**: Convidar usuário, aceitar convite, confirmar mesmo nível de permissão, e confirmar bloqueio ao tentar remover o único moderador restante.

- [ ] T084 [P] [US10] Contract test invite/accept/remove moderator in `backend/tests/contract/test_moderators.py`
- [ ] T085 [US10] Implement moderator invite/accept/remove endpoints with last-moderator guard in `backend/apps/catalog/views.py`
- [ ] T086 [P] [US10] Build moderator management UI (convidar, listar, remover) in `frontend/src/app/decks/[id]/moderators/page.tsx`

**Checkpoint**: US10 funciona isoladamente

---

## Phase 14: User Story 12 - Gestão de conta e privacidade (LGPD) (Priority: P3)

**Goal**: Usuário controla exclusão com carência de 7 dias e exportação de dados em JSON (FR-046, FR-047).

**Independent Test**: Solicitar exclusão, cancelar dentro do prazo, solicitar exportação e confirmar JSON com dados pessoais/sugestões/comentários.

- [ ] T087 [P] [US12] Contract test deletion-request and export in `backend/tests/contract/test_account_privacy.py`
- [ ] T088 [US12] Implement deletion-request schedule/cancel and 7-day grace job in `backend/apps/accounts/views.py`, `jobs.py`
- [ ] T089 [US12] Implement JSON data-export endpoint in `backend/apps/accounts/views.py`
- [ ] T090 [P] [US12] Build "Minha conta" privacy screen (consentimentos, exportar, excluir) in `frontend/src/app/account/privacy/page.tsx`

**Checkpoint**: US12 funciona isoladamente

---

## Phase 15: User Story 13 - Denúncia de conteúdo abusivo (Priority: P3)

**Goal**: Denunciar comentário/mensagem de sugestão; administrador revisa via Django admin (FR-048 a FR-051).

**Independent Test**: Denunciar um comentário, revisar e remover pelo Django admin, confirmar soft-ban reversível e e-mail de notificação ao autor removido.

- [ ] T091 [P] [US13] Contract test report creation on comments/suggestion-comments in `backend/tests/contract/test_reports.py`
- [ ] T092 [US13] Create Report model and report-creation endpoints in `backend/apps/discussions/models.py`, `views.py`
- [ ] T093 [US13] Register Report in Django admin with remove-content and suspend-author actions in `backend/apps/discussions/admin.py`
- [ ] T094 [US13] Implement synchronous email notification to removed-content author in `backend/apps/discussions/admin.py`
- [ ] T095 [P] [US13] Build "Denunciar" button on comments and suggestion messages in `frontend/src/components/ReportButton.tsx`

**Checkpoint**: Todas as 13 user stories funcionais independentemente

---

## Phase 16: Polish & Cross-Cutting Concerns

- [ ] T096 [P] Audit mobile-first 360px layout (sem rolagem horizontal) em todas as páginas de `frontend/src/`
- [ ] T097 [P] Add `Accept`-header API version negotiation middleware + teste de compatibilidade retroativa in `backend/config/middleware.py`
- [ ] T098 [P] Verify Sentry captures errors end-to-end in `backend/` and `addon/`
- [ ] T099 Run quickstart.md validation scenarios 1–3 end-to-end
- [ ] T100 [P] Security hardening pass: confirm `nh3` allowlist, rate limits, HTTPS-only settings in `backend/config/settings/`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: depende de Setup — bloqueia todas as user stories
- **US1, US2, US3, US4, US5 (P1, Phases 3-7)**: dependem só de Foundational; **US3** é o alvo mais crítico do MVP (entrega a proposta de valor central) e **US5** fecha o ciclo iniciado por **US4** — ambas ainda são independentemente testáveis
- **US6, US7, US8, US9, US11 (P2, Phases 8-12)**: dependem só de Foundational (podem rodar em paralelo entre si e com P1, se houver capacidade)
- **US10, US12, US13 (P3, Phases 13-15)**: dependem só de Foundational
- **Polish (Phase 16)**: depende de todas as user stories desejadas estarem completas

### Notas de acoplamento (não bloqueiam independência, mas compartilham modelos)

- `Suggestion`/`SuggestionTargetNote` (US4) são reutilizados por US5, US8, US9 — implementar US4 primeiro na ordem sugerida evita retrabalho, mas cada story continua testável isoladamente com fixtures próprias.
- `Comment` (US5) é reutilizado por US7 e denunciado por US13.
- `DeckModerator` (Foundational) é consultado por US5 (permissão de aceitar/rejeitar) e gerenciado por US10 (convite/remoção).

### Parallel Opportunities

- Todas as tarefas [P] de uma mesma fase podem rodar em paralelo (arquivos distintos)
- Após Foundational, US1-US5 (P1) podem ser distribuídas entre desenvolvedores diferentes em paralelo
- Após Foundational, US6/US7/US8/US9/US11 (P2) e US10/US12/US13 (P3) também podem rodar em paralelo entre si

---

## Parallel Example: User Story 3 (a mais crítica)

```bash
# Testes de contrato e pytest-anki em paralelo (arquivos diferentes):
Task: "Contract test GET /decks/{id}/sync/delta/ in backend/tests/contract/test_sync_delta.py"
Task: "Contract test GET /decks/{id}/sync/full/ in backend/tests/contract/test_sync_full.py"
Task: "Contract test GET /media/{content_hash}/ in backend/tests/contract/test_sync_media.py"
Task: "pytest-anki test: delta apply order in addon/tests/unit/test_delta_apply.py"
Task: "pytest-anki test: backup+rollback in addon/tests/unit/test_sync_failure_recovery.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1–5, todas P1)

1. Completar Phase 1: Setup
2. Completar Phase 2: Foundational (bloqueia tudo)
3. Completar Phases 3-7 (US1 → US2 → US3 → US4 → US5) — nesta ordem, pois cada uma valida um elo do
   loop essencial (cadastro → catálogo → sync → sugestão → moderação) descrito no PRD
4. **PARAR e VALIDAR**: rodar cenários 1 e 2 de `quickstart.md`
5. Demonstrar/lançar o MVP com as 5 stories P1

### Incremental Delivery

1. Setup + Foundational → base pronta
2. US1 → US2 → US3 → US4 → US5 → MVP completo e demonstrável
3. US6, US7, US8, US9, US11 (P2) → qualidade de conteúdo e proteção de dados pessoais
4. US10, US12, US13 (P3) → co-moderação, LGPD e moderação de abuso, antes do lançamento público
5. Cada story soma valor sem quebrar as anteriores

### Parallel Team Strategy

Com múltiplos desenvolvedores, após Foundational:
- Dev A: US3 (sincronização — a mais complexa, isola bem em backend `apps/sync/` + `addon/`)
- Dev B: US1 + US2 (onboarding e catálogo)
- Dev C: US4 + US5 (sugestão e moderação)
- P2/P3 distribuídas conforme capacidade, todas paralelizáveis entre si após o MVP P1

---

## Notes

- [P] = arquivos diferentes, sem dependência entre si
- [US#] mapeia a tarefa à user story correspondente do spec.md, para rastreabilidade
- Escrever os testes de contrato antes da implementação de cada endpoint (falham primeiro, depois passam)
- Commit após cada tarefa ou grupo lógico
- Parar em qualquer checkpoint para validar a story isoladamente antes de seguir

---

## Phase 17: Convergence

**Purpose**: Lacunas entre spec/plan/contracts e o tasks.md original, detectadas por /speckit-converge em 2026-07-12 — trabalho não coberto por nenhuma tarefa existente (T017–T100 seguem válidas e não são duplicadas aqui)

- [ ] T101 [CRITICAL] Implement add-on login dialog and Supabase Auth token acquisition/storage (feeding `AnkiHubBrClient`) in `addon/ankihub_br/gui/` per FR-031 / plan: addon gui login dialog (missing)
- [ ] T102 Implement add-on deck publish/upload flow (export local deck → `POST /api/v1/decks/{id}/publish/` with note types, notes, media) in `addon/ankihub_br/main/` and `addon/ankihub_br/gui/` per plan: contracts/sync.md publish endpoint (missing)
- [X] T103 Add subdeck placement of notes to the backend data model (e.g. `Note.anki_deck_path` in `backend/apps/notes/models.py`) and include the subdecks segment in publish/delta/full payloads per FR-034 (missing)
- [X] T104 Create MediaFile model (`deck`, `content_hash`, `storage_path`, `original_filename`) in `backend/apps/notes/models.py` per plan: data-model MediaFile / FR-036 (missing)
- [ ] T105 Apply `RATELIMIT_SUGGESTION_RATE` via `@ratelimit` to suggestion-submission endpoints in `backend/apps/suggestions/views.py` per FR-052 (partial)
- [X] T106 Create `backend/.env.example` and `frontend/.env.local.example` referenced by quickstart.md setup steps per plan: quickstart.md (missing)

---

## Phase 18: Convergence

**Purpose**: Lacunas entre spec/plan/tasks e o código atual, detectadas por /speckit-converge em 2026-07-13 — depois da constituição v1.1.0 (Princípios VI/VII) e das atualizações de spec.md (FR-011, FR-055, SC-009) e plan.md (Tailwind/shadcn, research.md #13/#14); T017–T106 seguem válidas e não são duplicadas aqui

- [X] T107 Generate `frontend/design-system/MASTER.md` (palette, typography, tokens, base components, loading/empty/error states, global navigation — header, authenticated/anonymous menu, catálogo→deck→notas→sugestões flow) via `ui-ux-pro-max:design-system`, freely deciding palette/typography/light-dark strategy from the project's own analysis (no prescribed choice); MUST also resolve the currently-unreachable `.dark` tokens in `frontend/src/app/globals.css` (either wire a theme toggle or drop the unused dark tokens) before starting US4/US5 screen tasks (T051-T053, T064-T065) per plan: Constitution Check VII (missing)
- [ ] T108 Run an accessibility audit (labels, AA contrast, keyboard operability per FR-055/SC-009) across implemented MVP screens (`frontend/src/app/(auth)/`, `account/`, `decks/`) via `/impeccable audit`, fixing findings before new screens are added in `frontend/src/` (missing)
- [ ] T109 [P] Retrofit `frontend/src/app/(auth)/login,register,password-reset/page.tsx`, `account/page.tsx`, `decks/page.tsx`, `decks/[id]/page.tsx` from legacy `.form-page`/`.deck-list` CSS Modules classes onto Tailwind CSS 4 + shadcn/ui components, per Constitution Principle VII / research.md #14 (partial)
- [ ] T110 Confirm all UI copy, labels, and error messages across implemented screens (`frontend/src/app/`) are in pt-BR per FR-056 (missing)
