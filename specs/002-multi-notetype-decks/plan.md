# Implementation Plan: Suporte a Decks com Múltiplos Tipos de Nota

**Branch**: `002-multi-notetype-decks` | **Date**: 2026-07-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-multi-notetype-decks/spec.md`

## Summary

Remover a restrição de "um único tipo de nota por deck" imposta hoje só na importação inicial
(`addon/ankihub_br/main/publish.py`), e propagar a mudança até onde o backend ainda assume
implicitamente um `Deck.note_type` único: validação de sugestões, validação de proteção de campo, e o
gatilho de ressincronização completa por mudança estrutural. A abordagem escolhida é **puramente
aditiva e de baixo risco**: o caminho de leitura (sync `delta`/`full`, detalhe de nota) já é multi-tipo
por construção — `Note.note_type` já é uma FK própria por nota, independente do deck, desde o MVP
(`specs/001-ankihub-brasil-mvp/data-model.md:38`), e o add-on já consome `note_types: list[dict]` +
`note_type_id` por nota no sync (`addon/ankihub_br/main/sync.py:64-113,163`). Só o caminho de escrita
(publish/importação) e as validações que hoje leem `deck.note_type` diretamente precisam mudar.

## Technical Context

**Language/Version**: Python 3.12 (backend Django), Python (versão embutida no Anki LTS mais recente,
compatibilidade já fixada pelo spec MVP) para o add-on

**Primary Dependencies**: Django + DRF, `anki`/`aqt` (add-on) — nenhuma dependência nova

**Storage**: Postgres via Supabase (inalterado)

**Testing**: pytest (`backend/tests`, `addon/tests`), Playwright (`frontend/tests/e2e`) — inalterado

**Target Platform**: Heroku (backend), Anki Desktop LTS (add-on), Next.js (frontend) — inalterado

**Project Type**: Web app com add-on desktop (backend + frontend + addon), estrutura já existente

**Performance Goals**: Nenhuma meta nova; a busca de notas (<500ms até 10 mil notas, FR-010 do MVP)
não é afetada por esta mudança

**Constraints**: Constituição II (sync unidirecional, importação inicial create-only e atômica) segue
valendo sem exceção; nenhuma nova escrita do add-on para o backend além da importação inicial já
existente

**Scale/Scope**: Mudança cirúrgica em ~6 arquivos de backend (`catalog/models.py`, `sync/views.py`,
`protection/serializers.py`, `suggestions/serializers.py`, `suggestions/views.py`,
`suggestions/decisions.py`), 2 arquivos do add-on (`main/publish.py`, e o dicionário de payload em
`gui/__init__.py` se necessário), 1 migração de schema (não de dados), e uma pequena superfície de
frontend (US3: composição de tipos de nota no detalhe do deck)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| I. Parity Over Reinvention | Pass — nenhuma convenção nova é inventada; o contrato de sync (`note_types: list` + `note_type_id`/`note_type_index` por item) apenas estende um padrão que o próprio projeto já usa no caminho de leitura. |
| II. Unidirectional Sync (NON-NEGOTIABLE) | Pass — a importação inicial continua sendo a única escrita do add-on para o backend, continua create-only, continua atômica (`transaction.atomic()` em `PublishView.post`); esta mudança apenas amplia o que essa única transação pode conter (N tipos de nota em vez de 1). Nenhuma republicação ou push de edição local é introduzido. |
| III. LGPD by Design | N/A — nenhum dado pessoal novo é tratado. |
| IV. Secure by Default | Pass — `sanitize_field_values` continua rodando por nota antes de persistir (inalterado); nenhuma superfície HTTP nova é criada, só payloads existentes mudam de forma. |
| V. MVP Scope Discipline (YAGNI) | Pass — esta é exatamente a extensão que `data-model.md` do MVP já citava como "pode ser estendido a N no pós-MVP"; o plano explicitamente NÃO adiciona: edição de tipos de nota depois de publicados, criação de tipo de nota novo via sugestão (só permite escolher entre os tipos já existentes do deck), ou proteção de campo por tipo de nota (fica união de nomes de campo no nível do deck, como já era). |
| VI. Current Docs & Minimal Code | Pass — nenhuma dependência nova; reaproveita construções Django/DRF já usadas no projeto (`annotate`/`Count`, `select_related`, FK nullable). |
| VII. Design Tooling Pipeline | Aplica-se apenas à pequena superfície de frontend da US3 (lista de tipos de nota no detalhe do deck) — a implementação dessa tela específica MUST passar pelo pipeline `ui-ux-pro-max` → `impeccable` na fase de tasks/implementação, não neste plano. |

Nenhuma violação; `Complexity Tracking` fica vazio.

## Project Structure

### Documentation (this feature)

```text
specs/002-multi-notetype-decks/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── apps/
│   ├── catalog/
│   │   ├── models.py          # remove Deck.note_type FK; note_types derivado de Note
│   │   └── serializers.py     # DeckDetailSerializer: note_type único → note_types (lista + contagem)
│   ├── notes/
│   │   └── migrations/        # nova migração: remove catalog.Deck.note_type
│   ├── sync/
│   │   └── views.py           # _deck_payload monta note_types a partir das notas; PublishView aceita
│   │                           # note_types (lista) + note_type_index por nota; DeltaView checa
│   │                           # structure_changed_at por tipo de nota tocado, não só deck.note_type
│   ├── protection/
│   │   └── serializers.py     # valida contra união de field_names de todos os tipos de nota do deck
│   └── suggestions/
│       ├── models.py          # Suggestion.note_type FK nullable (só para type=new_note)
│       ├── serializers.py     # NewNoteSuggestionSerializer exige escolher um dos tipos existentes;
│       │                       # bulk change exige notas-alvo do mesmo tipo de nota
│       ├── views.py           # validação de campo por nota (não mais deck.note_type)
│       └── decisions.py       # accept de new_note usa suggestion.note_type, não deck.note_type
│
addon/
└── ankihub_br/
    └── main/
        └── publish.py          # remove guarda de tipo único; agrupa notas por mid; monta note_types
                                 # (lista) + note_type_index por nota exportada
│
frontend/
└── (US3) tela de detalhe do deck — exibe lista de tipos de nota + contagem por tipo
```

**Structure Decision**: reaproveita a estrutura Django-apps já existente no backend (`catalog`,
`notes`, `sync`, `protection`, `suggestions`) e o pacote único do add-on (`ankihub_br/main`); nenhum
app/módulo novo é criado — a mudança é de comportamento dentro dos módulos que já possuem essa
responsabilidade.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

Nenhuma violação — tabela intencionalmente vazia.
