---

description: "Task list for Suporte a Decks com Múltiplos Tipos de Nota"

---

# Tasks: Suporte a Decks com Múltiplos Tipos de Nota

**Input**: Design documents from `/specs/002-multi-notetype-decks/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: incluídas — o projeto já mantém um teste de contrato por endpoint tocado
(`backend/tests/contract/`) e testes unitários por módulo do add-on (`addon/tests/unit/`); esta
feature estende esse padrão existente em vez de introduzi-lo.

**Organization**: tarefas agrupadas por user story (US1/US2/US3 de `spec.md`), precedidas por uma fase
Foundational que é **obrigatória e bloqueante**: remover a FK `Deck.note_type` quebra imediatamente
todo código que a lê (mesmo para decks de tipo único hoje existentes), então corrigir cada ponto de
leitura faz parte do "colocar o chão de volta em pé", não de uma user story específica.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência entre si)
- **[Story]**: US1, US2 ou US3 — tarefas de Setup/Foundational/Polish não têm label

## Path Conventions

Web app existente: `backend/apps/...`, `backend/tests/...`, `addon/ankihub_br/...`,
`addon/tests/...`, `frontend/src/...`, `frontend/tests/...` (ver `plan.md` → Project Structure).

---

## Phase 1: Setup

Nenhuma tarefa de setup necessária — reaproveita projetos, dependências e ferramentas já configurados
(nenhuma dependência nova, ver `plan.md` → Technical Context).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: remover `Deck.note_type` sem quebrar nenhum comportamento hoje existente (SC-003); todo
ponto do backend que lia `deck.note_type` diretamente precisa passar a derivar da(s) nota(s) do deck
antes que qualquer user story possa ser implementada ou testada com segurança.

**⚠️ CRITICAL**: nenhuma tarefa de US1/US2/US3 pode começar antes desta fase — o test suite inteiro
(`pytest`) quebra assim que a FK sai do model até esta fase terminar.

- [ ] T001 Migração Django em `backend/apps/catalog/migrations/`: remove a FK `Deck.note_type`
      (`backend/apps/catalog/models.py:10-12`)
- [ ] T002 Migração Django em `backend/apps/suggestions/migrations/`: adiciona `Suggestion.note_type`
      (FK nullable → `notes.NoteType`, `on_delete=PROTECT`) em `backend/apps/suggestions/models.py`
- [ ] T003 Remove o campo `note_type` de `Deck` em `backend/apps/catalog/models.py:10-12` (aplicado
      pela migração T001); nenhum atributo substituto no model — tipos de nota do deck passam a ser
      derivados via `NoteType.objects.filter(notes__deck=deck).distinct()` (Decisão 1 de
      `research.md`)
- [ ] T004 Adiciona campo `note_type` (FK nullable) a `Suggestion` em
      `backend/apps/suggestions/models.py` (aplicado pela migração T002)
- [ ] T005 [P] Atualiza fixtures `make_deck`/`make_note` em `backend/tests/conftest.py:38-63` para não
      passar mais `note_type=` ao criar `Deck` (mantém em `Note`, que já tinha FK própria)
- [ ] T006 Corrige `protection/views.py:17` (`get_deck`) em `backend/apps/protection/views.py`: remove
      `select_related("note_type")` inválido (relação não existe mais no `Deck`)
- [ ] T007 Corrige `ProtectionConfigSerializer.validate_fields` em
      `backend/apps/protection/serializers.py:14-21`: valida contra a união dos `field_names` de
      todos os tipos de nota do deck (Decisão 4 de `research.md`), não mais `deck.note_type.field_names`
- [ ] T008 Corrige `_change_validation_error` em `backend/apps/suggestions/views.py:93-124`: resolve
      `field_names` esperado a partir do(s) `note_type` das notas-alvo (`notes[0].note_type`, já
      garantido único por T009), não mais `deck.note_type.field_names`
- [ ] T009 Adiciona validação em `BulkChangeSuggestionCreateView.post` em
      `backend/apps/suggestions/views.py:171-197`: rejeita com `400` se as notas de `note_ids`
      pertencerem a mais de um `NoteType` (novo invariante de `data-model.md` → "Regra de invariante
      nova")
- [ ] T010 Corrige `NewNoteSuggestionSerializer` em `backend/apps/suggestions/serializers.py:87-137`:
      adiciona campo obrigatório `note_type` (FK id), valida que pertence ao deck do contexto, resolve
      `expected` a partir desse `note_type.field_names` em vez de `self.context["deck"].note_type
      .field_names` (`:120`)
- [ ] T011 Corrige `NewNoteSuggestionCreateView.post` em `backend/apps/suggestions/views.py:210-230`:
      remove `select_related("note_type")` inválido em `Deck.objects...` (`:213`); persiste
      `note_type=serializer.validated_data["note_type"]` na criação da `Suggestion`
- [ ] T012 Corrige `SuggestionAcceptView.decide` (ramo `NEW_NOTE`) em
      `backend/apps/suggestions/decisions.py:83-92`: `Note.objects.create(...note_type=
      suggestion.note_type...)` em vez de `suggestion.deck.note_type`
- [ ] T013 Corrige `DeltaView.sync` em `backend/apps/sync/views.py:145-150`: troca
      `deck.note_type.structure_changed_at` por
      `NoteType.objects.filter(notes__deck=deck, structure_changed_at__gt=since).exists()` (Decisão 3
      de `research.md`)
- [ ] T014 Corrige `_deck_payload` em `backend/apps/sync/views.py:91-107`: monta `note_types` a partir
      dos tipos de nota distintos presentes em `notes` (o argumento já recebido, sem query extra) em
      vez de `[_note_type_payload(deck.note_type)]`
- [ ] T015 Roda a suíte de regressão completa (`cd backend && pytest -q`) e confirma que todos os
      testes de contrato existentes (`test_sync_delta.py`, `test_sync_full.py`, `test_protection.py`,
      `test_suggestions_*.py`, `test_catalog_list.py`) passam com decks de tipo único — sem esta
      confirmação, SC-003 (compatibilidade retroativa) não está garantida

**Checkpoint**: schema atualizado, todo `deck.note_type` legado corrigido, suíte de testes existente
verde para decks de tipo único — as user stories abaixo podem começar.

---

## Phase 3: User Story 1 - Publicar deck com tipos de nota mistos (Priority: P1) 🎯 MVP

**Goal**: importação inicial via add-on aceita um deck cujas notas pertencem a mais de um tipo de
nota, em vez de recusar com "A importação inicial aceita um único tipo de nota por deck."

**Independent Test**: publicar, via add-on, um deck local com notas de 2+ tipos de nota distintos;
deck aparece no catálogo com todas as notas associadas ao tipo correto, sem erro.

### Tests for User Story 1

- [ ] T016 [P] [US1] Atualiza `test_rejects_deck_with_multiple_note_types` em
      `addon/tests/unit/test_publish.py:62-81`: deck com 2 tipos de nota agora **deve ser aceito**
      (payload com `note_types` de 2 itens e `note_type_index` correto por nota), não mais rejeitado
- [ ] T017 [P] [US1] Novo teste de contrato em `backend/tests/contract/test_sync_publish.py`: `POST
      .../publish/` com `note_types: [...]` (2+ itens) cria um `NoteType` por item e associa cada
      `Note` pelo `note_type_index` correto
- [ ] T018 [P] [US1] Novo teste de contrato em `backend/tests/contract/test_sync_publish.py`:
      `note_type_index` fora do intervalo de `note_types` responde `400`

### Implementation for User Story 1

- [ ] T019 [US1] Reescreve `build_publish_payload` em `addon/ankihub_br/main/publish.py:25-89`: remove
      a guarda `len(notetype_ids) != 1`; agrupa `notes` por `note.mid`; monta `note_types` (lista, uma
      entrada por grupo, na ordem de primeira ocorrência) e adiciona `note_type_index` a cada nota
      exportada (Decisão 2/5 de `research.md`)
- [ ] T020 [US1] Atualiza `PublishView.post` em `backend/apps/sync/views.py:238-283`: lê
      `data.get("note_types")` (lista) em vez de `data.get("note_type")` (objeto único); cria um
      `NoteType` por item da lista dentro da mesma `transaction.atomic()`; valida `name`/
      `note_types[].field_names` obrigatórios (`400` se ausentes); resolve `Note.note_type` de cada
      item de `data["notes"]` pelo seu `note_type_index` (`400` se fora do intervalo)

**Checkpoint**: decks multi-tipo publicam com sucesso ponta-a-ponta (add-on → backend); decks de tipo
único continuam publicando exatamente como antes.

---

## Phase 4: User Story 2 - Assinante sincroniza e revisa notas de tipos diferentes (Priority: P2)

**Goal**: um deck com múltiplos tipos de nota sincroniza corretamente para o Anki local e cada nota
renderiza com o template/CSS do seu próprio tipo, tanto no Anki quanto no preview web.

**Independent Test**: sincronizar um deck com 2 tipos de nota para um perfil Anki limpo; cada tipo é
recriado com seus templates/CSS; preview web de uma nota de cada tipo usa o template correto.

### Tests for User Story 2

- [ ] T021 [P] [US2] Novo teste em `backend/tests/contract/test_sync_full.py`: `GET .../sync/full/`
      de um deck com 2 tipos de nota retorna `note_types` com os 2 itens e cada nota com o
      `note_type_id` correto
- [ ] T022 [P] [US2] Novo teste em `backend/tests/contract/test_sync_delta.py`: mudança estrutural
      (nº de templates) em **um** dos tipos de nota de um deck multi-tipo dispara
      `full_resync_required=true`, mesmo sem mudança no outro tipo
- [ ] T023 [P] [US2] Novo teste em `addon/tests/unit/test_delta_apply.py`: payload de `sync/full` com
      `note_types` de 2 itens recria os dois tipos de nota locais e associa cada nota pelo
      `note_type_id` correto (estende os testes já existentes em torno de `_apply_note_types`)

### Implementation for User Story 2

- [ ] T024 [US2] Confirma (sem alteração de código esperada, só validação manual via
      `quickstart.md` → Cenário 2) que `GET /api/v1/notes/{id}/` já isola corretamente
      `note_type.templates`/`note_type.css` por nota — contrato já é per-note desde o MVP
      (`specs/001-ankihub-brasil-mvp/contracts/notes.md`); registra o resultado da checagem no PR

**Checkpoint**: sincronização e preview corretos para decks multi-tipo — a maior parte do trabalho
real desta história já foi resolvida na Fase 2 (Foundational); esta fase é majoritariamente prova/teste.

---

## Phase 5: User Story 3 - Moderador visualiza composição de tipos de nota do deck (Priority: P3)

**Goal**: o moderador/criador vê, no detalhe do deck, quantos tipos de nota distintos existem e
quantas notas há por tipo.

**Independent Test**: publicar um deck com 3 tipos de nota; detalhe do deck mostra os 3 tipos e a
contagem de notas de cada um, batendo com a origem.

### Tests for User Story 3

- [ ] T025 [P] [US3] Atualiza `test_detail_exposes_only_non_sensitive_moderator_state` em
      `backend/tests/contract/test_catalog_list.py:58-77`: espera `note_types` (lista) em vez de
      `note_type` (objeto único); novo teste no mesmo arquivo cobre deck com 3 tipos de nota e
      confere `note_count` por tipo
- [ ] T026 [P] [US3] Atualiza o mock de deck detail em `frontend/tests/e2e/p1-flow.spec.ts:117-127`
      para `note_types: [...]` (lista)

### Implementation for User Story 3

- [ ] T027 [US3] Substitui `DeckDetailSerializer.get_note_type` por `get_note_types` em
      `backend/apps/catalog/serializers.py:24-51`: retorna lista `[{id, name, field_names,
      note_count}]` via uma única query agregada (`Note.objects.filter(deck=deck,
      deleted_at__isnull=True).values("note_type").annotate(count=Count("id"))`), sem N+1 (Decisão 6
      de `research.md`); atualiza `fields` de `DeckDetailSerializer.Meta` (`note_type` → `note_types`)
- [ ] T028 [US3] Atualiza `DeckDetail` (interface TS) e uso em
      `frontend/src/app/decks/[id]/protection/page.tsx:16-22,211`: consome `note_types[]`; para o
      formulário de proteção de campo, usa a **união** dos `field_names` de todos os tipos (mesma
      regra do backend, T007) — protege por nome de campo, não por tipo
- [ ] T029 [US3] Atualiza `DeckDetail` (interface TS) e uso em
      `frontend/src/app/decks/[id]/suggest-new-note/page.tsx:18-25,57,139,155,164`: consome
      `note_types[]`; adiciona seletor de tipo de nota quando o deck tem mais de um (envia
      `note_type` no payload de `POST .../suggestions/new-note/`, conforme
      `contracts/suggestions.md`); esta tela específica MUST passar pelo pipeline
      `ui-ux-pro-max` → `impeccable` antes de ser considerada pronta (Constituição VII)

**Checkpoint**: todas as três user stories funcionam de forma independente; deck multi-tipo é
publicável, sincronizável e visível com sua composição real de tipos de nota.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T030 [P] Atualiza `specs/001-ankihub-brasil-mvp/data-model.md:38` (nota "pode ser estendido a N
      no pós-MVP") para referenciar esta feature como a extensão realizada
- [ ] T031 Roda `specs/002-multi-notetype-decks/quickstart.md` ponta-a-ponta (4 cenários) antes de
      considerar a feature pronta

---

## Dependencies & Execution Order

### Phase Dependencies

- **Foundational (Phase 2)**: sem dependências externas — mas **bloqueia** todas as user stories
  (T001–T015 antes de qualquer tarefa US1/US2/US3)
- **User Story 1 (Phase 3)**: depende só de Foundational
- **User Story 2 (Phase 4)**: depende só de Foundational — não depende de US1 para os testes que
  exercitam o backend/add-on diretamente com fixtures multi-tipo, mas o cenário de validação manual
  ponta-a-ponta (`quickstart.md` → Cenário 2) precisa de um deck publicado por US1
- **User Story 3 (Phase 5)**: depende só de Foundational — igualmente, a validação manual ponta-a-ponta
  precisa de um deck publicado por US1
- **Polish (Phase 6)**: depende de todas as stories desejadas estarem completas

### Within Each User Story

- Testes antes da implementação correspondente
- US1: add-on (T019) e backend (T020) são interdependentes no fluxo real (o add-on é quem monta o
  payload que o backend consome), mas os arquivos são independentes — podem ser implementados em
  paralelo e integrados depois
- US3: backend (T027) antes do frontend (T028, T029) — frontend consome o novo formato de resposta

### Parallel Opportunities

- T016, T017, T018 (testes de US1) em paralelo
- T021, T022, T023 (testes de US2) em paralelo
- T025, T026 (testes de US3) em paralelo
- T028, T029 (duas telas de frontend distintas) em paralelo entre si, ambas após T027
- Dentro da Foundational: T005 pode rodar em paralelo com T006–T014 (arquivo diferente); T006/T007
  (protection) em paralelo com T008–T012 (suggestions) e com T013/T014 (sync) — todos arquivos
  distintos, sem dependência mútua

---

## Parallel Example: User Story 1

```bash
Task: "Atualiza test_rejects_deck_with_multiple_note_types em addon/tests/unit/test_publish.py"
Task: "Novo teste de contrato em backend/tests/contract/test_sync_publish.py (note_types multi-item)"
Task: "Novo teste de contrato em backend/tests/contract/test_sync_publish.py (note_type_index inválido)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Completar Phase 2: Foundational (obrigatório — sem isso nada roda)
2. Completar Phase 3: User Story 1
3. **PARAR e VALIDAR**: publicar um deck real com 2 tipos de nota via add-on, confirmar no catálogo
4. Deploy/demo se pronto — já resolve a dor original relatada (bug `multi-notetype-import-error`)

### Incremental Delivery

1. Foundational → base estável, zero regressão (SC-003)
2. US1 → publicar decks mistos (MVP!)
3. US2 → confirmar sync/preview corretos (grande parte já garantida pela Foundational)
4. US3 → visibilidade da composição de tipos no detalhe do deck

---

## Notes

- [P] tasks = arquivos diferentes, sem dependência
- Toda a "correção de compatibilidade" (T006–T014) é Foundational porque remover `Deck.note_type`
  quebra decks de **tipo único** também — não é trabalho específico de nenhuma user story
- Rodar `pytest`/testes do add-on após cada tarefa ou grupo lógico
- Parar em qualquer checkpoint para validar a história isoladamente
